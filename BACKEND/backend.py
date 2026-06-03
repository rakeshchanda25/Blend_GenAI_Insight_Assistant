import logging
from langgraph.graph import StateGraph, END
from pydantic_models import AgentState, QueryPlan, ValidationResult
from utils import GeminiClient, parse_json_response, dataframe_to_text, detect_sql_injection, validate_sql_whitelist
from prompt_template import (
    QUERY_CLASSIFICATION_PROMPT,
    FULL_DATA_SUMMARIZATION_PROMPT,
    VALIDATION_PROMPT,
    CONVERSATIONAL_PROMPT
)
from tools import (
    execute_sqlite_query,
    get_sqlite_schema,
    retrieve_from_chromadb,
    format_rag_context,
    query_sqlite_tool,
    query_chromadb_tool,
    get_last_generated_sql,
    reset_last_generated_sql
)
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GEMINI_API_KEY, LLM_CONFIG

logger = logging.getLogger(__name__)

llm = GeminiClient()


# ============== ROUTING LOGIC ==============

def get_data_source(query_type: str, user_query: str = "") -> str:
    """
    Determine data source based on query type and content.

    Returns: "sqlite" | "chromadb" | "hybrid"
    """
    # Structured query types → SQLite
    structured = ['aggregation', 'ranking', 'comparison', 'trend', 'filter', 'count', 'sum', 'average']
    if query_type.lower() in structured:
        return "sqlite"

    # Semantic query types → ChromaDB
    semantic = ['insight', 'summary', 'recommendation', 'analysis', 'explanation']
    if query_type.lower() in semantic:
        return "chromadb"

    # Default to SQLite for structured data
    return "sqlite"

######################### AGENT FUNCTIONS ###########################

def query_interpretation_agent(state: AgentState) -> AgentState:
    """Agent 1: Parse natural language query into structured plan."""
    logger.info("Running Query Interpretation Agent")

    # schema = get_data_schema()
    prompt = QUERY_CLASSIFICATION_PROMPT.format(
        query=state["user_query"])
    try:
        result = llm.generate_json(prompt)
        query_intent = QueryPlan(**result) if result else QueryPlan(
            query_type="converstaional",
            intent="answer",
            confidence=0.5
        )
        state["query_intent"] = query_intent.model_dump()
        logger.info(f"Query plan: {state['query_intent']}")
    except Exception as e:
        logger.error(f"Interpretation error: {e}")
        state["query_intent"] = {"query_type": "converstaional", "intent": "answer", "confidence": 0.3}
        state["error"] = str(e)
    return state

def data_extraction_agent(state: AgentState) -> AgentState:
    """Agent 2: Based on user query, retrieve relevant data and summarize it.
    Logic:
    - If query_type = "summarize": Get ALL data from both sources, provide comprehensive summary
    - If query_type = "conversational": Use LangChain agent with tools to autonomously explore and decide data source
    """
    logger.info("Running Data Extraction Agent")

    query_type = state.get("query_intent", {}).get("query_type", "conversational")
    user_query = state.get("user_query", "")

    try:
        if query_type == "summarize":
            logger.info("Summarization mode: retrieving all data")

            # 1. Get ALL SQLite data (use .invoke() for @tool decorated functions)
            sql = "SELECT * FROM sales_data"  # Limit for performance
            state["generated_sql"] = sql  # Track SQL for validation
            sqlite_result = execute_sqlite_query.invoke({"sql": sql})

            # 2. Get ALL ChromaDB data (with graceful error handling)
            formatted_context = ""
            chromadb_available = False
            try:
                chromadb_result = retrieve_from_chromadb.invoke({
                    "query": "sales insights summary",
                    "n_results": 20
                })
                if chromadb_result.get("success") and chromadb_result.get("documents"):
                    formatted_context = format_rag_context.invoke({"rag_results": chromadb_result})
                    chromadb_available = True
                else:
                    logger.info("ChromaDB has no data - skipping semantic context")
            except Exception as chromadb_error:
                logger.warning(f"ChromaDB not available: {chromadb_error}")
                formatted_context = "No semantic documents available."

            # 3. Prepare comprehensive data for LLM
            sqlite_records = sqlite_result.get("rows", 0)
            sqlite_data = sqlite_result.get("data", [])[:50]  # Show first 50 as sample

            data_sources = ["sqlite"]
            if chromadb_available:
                data_sources.append("chromadb")

            combined_data = {
                "sqlite_records": sqlite_records,
                "sqlite_preview": sqlite_data,
                "chromadb_context": formatted_context,
                "data_sources": data_sources
            }

            # 4. Generate full summary using LLM
            prompt = FULL_DATA_SUMMARIZATION_PROMPT.format(
                sqlite_records=sqlite_records,
                sqlite_data=str(sqlite_data)[:],  # Limit to 2000 chars
                chromadb_context=formatted_context[:] if formatted_context else "No documents available"
            )
            response = llm.generate(prompt)

            state["extracted_data"] = combined_data
            state["response"] = response
            state["data_source"] = "hybrid" if chromadb_available else "sqlite"

            logger.info(f"Summarization complete. SQLite records: {sqlite_records}, ChromaDB available: {chromadb_available}")

        else:  # conversational mode - LangChain agent
            logger.info("Conversational mode: Starting LangChain agent with tools")

            #  Define tools (already decorated with @tool)
            tools = [query_sqlite_tool, query_chromadb_tool]

            #  Create LLM for agent
            try:
                llm_for_agent = ChatGoogleGenerativeAI(
                    model=LLM_CONFIG.get("model", "gemini-1.5-flash"),
                    google_api_key=GEMINI_API_KEY,
                    temperature=LLM_CONFIG.get("temperature", 0.3),
                    max_output_tokens=LLM_CONFIG.get("max_tokens", 2048)
                )
            except Exception as llm_error:
                logger.warning(f"ChatGoogleGenerativeAI init failed: {llm_error}, using fallback")
                llm_for_agent = llm  # Fallback to existing client

            # 4. Create and run agent (new LangChain 1.3+ API)
            agent = create_agent(
                model=llm_for_agent,
                tools=tools,
                system_prompt=CONVERSATIONAL_PROMPT
            )

            # 5. Run agent with user query (agent is now a CompiledStateGraph)
            result = agent.invoke({"messages": [{"role": "user", "content": user_query}]})

            # 6. Extract and return response
            # The result contains messages, get the last AI message
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]

                # Extract content - handle both string and list formats
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    # If content is a list of blocks, extract text
                    if isinstance(content, list):
                        response_text = ""
                        for block in content:
                            if isinstance(block, dict) and 'text' in block:
                                response_text += block['text']
                            elif isinstance(block, str):
                                response_text += block
                        response_text = response_text.strip() or "No response generated"
                    else:
                        response_text = str(content)
                else:
                    response_text = str(last_message)

                state["response"] = response_text
            else:
                state["response"] = "No response generated"

            state["data_source"] = "langchain_agent"
            state["extracted_data"] = None  # Agent handles data internally

            # Track SQL generated by the tool (if any)
            last_sql = get_last_generated_sql()
            if last_sql:
                state["generated_sql"] = last_sql
                reset_last_generated_sql()  # Reset for next query

        logger.info(f"Data extraction complete. Source: {state.get('data_source')}")

    except Exception as e:
        logger.error(f"Data extraction error: {e}", exc_info=True)
        state["error"] = str(e)
        state["response"] = f"Error retrieving data: {str(e)}"
        state["extracted_data"] = None

    return state

# ============== VALIDATOR AGENT ==============

def validator_agent(state: AgentState) -> AgentState:
    """Agent 3: Validate response quality and security before returning to user.

    Performs three types of validation:
    1. SQL Security: Checks generated SQL for injection patterns
    2. Relevance: Uses LLM to verify response answers the query
    3. Data Quality: Uses LLM to check accuracy and completeness

    Args:
        state: Current agent state with response to validate

    Returns:
        Updated state with validation_result and potentially modified response
    """
    logger.info("Running Validator Agent")

    issues = []
    confidence = 1.0

    # ============== STEP 1: SQL Security Validation ==============
    generated_sql = state.get("generated_sql")
    if generated_sql:
        logger.info("Checking SQL for injection patterns")

        # Blacklist check (detect dangerous patterns)
        is_safe, sql_issues = detect_sql_injection(generated_sql)
        if not is_safe:
            issues.extend([f"SECURITY: {issue}" for issue in sql_issues])
            confidence -= 0.3
            logger.warning(f"SQL security issues detected: {sql_issues}")

        # Whitelist check (only allow safe patterns)
        is_allowed, whitelist_issues = validate_sql_whitelist(generated_sql)
        if not is_allowed:
            issues.extend([f"SECURITY: {issue}" for issue in whitelist_issues])
            confidence -= 0.2
            logger.warning(f"SQL whitelist issues: {whitelist_issues}")

    # ============== STEP 2: Response Validation via LLM ==============
    response = state.get("response", "")
    user_query = state.get("user_query", "")

    if response and user_query:
        # Skip LLM validation if we already have critical security issues
        security_issues = [i for i in issues if "SECURITY" in i]
        if not security_issues:
            try:
                validation_prompt = VALIDATION_PROMPT.format(
                    user_query=user_query,
                    response=response[:2000],  # Limit for token efficiency
                    query_intent=state.get("query_intent", {}),
                    data_source=state.get("data_source", "unknown")
                )

                validation_result = llm.generate_json(validation_prompt)

                if validation_result:
                    # Extract validation details
                    llm_issues = validation_result.get("issues", [])
                    relevance_score = validation_result.get("relevance_score", 0.5)
                    quality_score = validation_result.get("quality_score", 0.5)
                    recommendation = validation_result.get("recommendation", "pass")

                    # Aggregate issues
                    issues.extend([f"QUALITY: {issue}" for issue in llm_issues])

                    # Adjust confidence based on scores
                    if relevance_score < 0.5:
                        confidence -= 0.2
                        issues.append("RELEVANCE: Response may not fully answer the question")

                    if quality_score < 0.5:
                        confidence -= 0.2
                        issues.append("QUALITY: Response quality is below threshold")

                    # Store detailed scores in metadata
                    if state.get("metadata") is None:
                        state["metadata"] = {}
                    state["metadata"]["validation_scores"] = {
                        "relevance": relevance_score,
                        "quality": quality_score,
                        "recommendation": recommendation
                    }

                    logger.info(f"LLM validation: relevance={relevance_score}, quality={quality_score}")

            except Exception as e:
                logger.warning(f"LLM validation failed: {e}")
                # Don't fail validation just because LLM call failed
                issues.append(f"WARNING: Could not perform LLM validation: {str(e)}")

    # ============== STEP 3: Build Final Validation Result ==============
    # Only fail on SECURITY issues - quality/relevance issues are logged but don't block
    security_issues = [i for i in issues if "SECURITY" in i]
    is_valid = len(security_issues) == 0
    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

    validation_result = ValidationResult(
        is_valid=is_valid,
        confidence=confidence,
        issues=issues
    )

    state["validation_result"] = validation_result.model_dump()
    state["is_validated"] = is_valid

    # ============== STEP 4: Handle Validation Failure ==============
    # Only block response for SECURITY issues, not quality/relevance
    if not is_valid:
        logger.warning(f"Validation failed (security): {security_issues}")

        # Create user-friendly error message
        error_message = _format_validation_error(issues, user_query)
        state["response"] = error_message
        state["error"] = "Validation failed"
    elif issues:
        # Log non-critical issues but don't block the response
        logger.info(f"Validation passed with warnings: {issues}")

    logger.info(f"Validation complete: valid={is_valid}, confidence={confidence}")
    return state


def _format_validation_error(issues: list, user_query: str) -> str:
    """Format validation issues into a user-friendly error message.

    Args:
        issues: List of validation issues
        user_query: Original user query for context

    Returns:
        Formatted error message string
    """
    # Categorize issues
    security_issues = [i for i in issues if "SECURITY" in i]
    quality_issues = [i for i in issues if "QUALITY" in i]
    relevance_issues = [i for i in issues if "RELEVANCE" in i]

    message_parts = ["I apologize, but I couldn't provide a valid response to your question."]

    if security_issues:
        message_parts.append("\n\n**Security Notice:** The query was blocked for security reasons. Please rephrase your question without any SQL-like syntax.")

    if relevance_issues:
        message_parts.append("\n\n**Relevance Issue:** The generated response may not fully answer your question. Please try rephrasing or being more specific.")

    if quality_issues:
        message_parts.append("\n\n**Quality Issue:** The data quality check identified potential issues with the response accuracy or completeness.")

    message_parts.append("\n\n**Suggestion:** Please try asking your question in a different way, or contact support if the issue persists.")
    message_parts.append(f"\n\nOriginal question: \"{user_query}\"")

    return "".join(message_parts)


def error_response_node(state: AgentState) -> AgentState:
    """Handle validation failure - format error response for user.

    This node is reached when validation fails. The response has already
    been updated by validator_agent with the error message.

    Args:
        state: Current state with validation failure info

    Returns:
        State ready to return to user
    """
    logger.info("Processing validation error response")

    # Log the validation failure for monitoring
    validation_result = state.get("validation_result", {})
    logger.warning(f"Returning error response to user. Issues: {validation_result.get('issues', [])}")

    # Ensure metadata contains validation info for frontend
    if state.get("metadata") is None:
        state["metadata"] = {}

    state["metadata"]["validation_failed"] = True
    state["metadata"]["validation_issues"] = validation_result.get("issues", [])

    return state


def route_after_validation(state: AgentState) -> str:
    """Route based on validation result.

    Returns:
        'end' if validation passed, 'error_response' if failed
    """
    if state.get("is_validated", False):
        return "end"
    else:
        return "error_response"


# ============== LANGGRAPH STATE MACHINE ==============

def route_after_interpretation(state: AgentState) -> str:
    """Route to data extraction agent."""
    return "data_extraction"


def build_agent_graph():
    """Build the LangGraph state machine for the agent pipeline.

    Pipeline flow:
    1. query_interpretation -> Classify and parse user query
    2. data_extraction -> Retrieve data and generate response
    3. validator -> Validate response quality and security
    4. Conditional routing:
       - If valid -> END (return response to user)
       - If invalid -> error_response -> END (return error message)
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("query_interpretation", query_interpretation_agent)
    graph.add_node("data_extraction", data_extraction_agent)
    graph.add_node("validator", validator_agent)
    graph.add_node("error_response", error_response_node)

    # Set entry point
    graph.set_entry_point("query_interpretation")

    # Add edges - linear flow to validator
    graph.add_edge("query_interpretation", "data_extraction")
    graph.add_edge("data_extraction", "validator")

    # Conditional routing after validation
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "end": END,
            "error_response": "error_response"
        }
    )

    # Error response leads to END
    graph.add_edge("error_response", END)

    return graph.compile()


# ============== ASSISTANT WRAPPER CLASS ==============

class RetailInsightsAssistant:
    """Main assistant that runs the agent pipeline.

    Note: Data loading (CSV to SQLite/ChromaDB) should be done separately
    using dedicated data loading scripts.
    """

    def __init__(self):
        """Initialize the assistant with compiled graph."""
        self.graph = build_agent_graph()
        logger.info("Retail Insights Assistant initialized")

    def get_data_info(self):
        """Get information about currently loaded data.

        Returns:
            dict with total_records and columns
        """
        try:
            # Use .invoke() for @tool decorated functions
            schema = get_sqlite_schema.invoke({})
            columns = schema.split(", ") if schema else []

            # Get record count
            result = execute_sqlite_query.invoke({"sql": "SELECT COUNT(*) as count FROM sales_data"})
            total_records = 0
            if result.get("success") and result.get("data"):
                total_records = result["data"][0].get("count", 0)

            return {
                "total_records": total_records,
                "columns": columns
            }

        except Exception as e:
            logger.error(f"Error getting data info: {e}")
            return {
                "total_records": 0,
                "columns": []
            }

    def ask(self, question: str) -> str:
        """Ask the assistant a question.

        Args:
            question: User's question

        Returns:
            Assistant's response
        """
        try:
            # Run the agent graph
            initial_state = {
                "user_query": question,
                "query_intent": None,
                "data_source": None,
                "extracted_data": None,
                "response": None,
                "error": None,
                "metadata": None,
                "validation_result": None,
                "generated_sql": None,
                "is_validated": None
            }

            result = self.graph.invoke(initial_state)
            response = result.get("response", "No response generated")

            logger.info(f"Question answered: {question[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return f"Error processing question: {str(e)}"

    def summarize(self) -> str:
        """Generate a comprehensive summary of all loaded data.

        Returns:
            Comprehensive summary string
        """
        try:
            # Create a summarization query
            summary_query = "Provide a comprehensive summary of all the sales data"

            # Run the agent graph with summarization intent
            initial_state = {
                "user_query": summary_query,
                "query_intent": {
                    "query_type": "summarize",
                    "intent": "summarize",
                    "confidence": 0.95
                },
                "data_source": None,
                "extracted_data": None,
                "response": None,
                "error": None,
                "metadata": None,
                "validation_result": None,
                "generated_sql": None,
                "is_validated": None
            }

            result = self.graph.invoke(initial_state)
            response = result.get("response", "No summary generated")

            logger.info("Summary generated")
            return response

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"


# Create global assistant instance
assistant = RetailInsightsAssistant()

