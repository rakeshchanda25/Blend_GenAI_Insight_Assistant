# Retail Insights Assistant - Complete System Flow Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Complete Data Flow](#complete-data-flow)
4. [Component Details](#component-details)
5. [API Endpoints Flow](#api-endpoints-flow)
6. [Agent Pipeline Flow](#agent-pipeline-flow)
7. [Tool Execution Flow](#tool-execution-flow)

---

## System Overview

**Purpose**: An AI-powered retail analytics assistant that answers questions about sales data using a multi-agent system with LangChain framework.

**Key Features**:
- Dual data storage (SQLite for structured data, ChromaDB for semantic search)
- LangChain-powered autonomous agent with tool calling
- Multi-agent pipeline with LangGraph orchestration
- FastAPI REST endpoints

---

## Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                  (Frontend / API Client)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI ENDPOINTS                          │
│  /ask  /summarize  /data-status  /upload  /data-info           │
│                        (main.py)                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              RetailInsightsAssistant (backend.py)               │
│  - Orchestrates agent pipeline                                 │
│  - Manages LangGraph state machine                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH PIPELINE                           │
│   ┌──────────────────┐         ┌───────────────────┐           │
│   │  Agent 1:        │────────>│  Agent 2:         │           │
│   │  Query           │         │  Data             │           │
│   │  Interpretation  │         │  Extraction       │           │
│   └──────────────────┘         └───────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ↓
                    ┌────────┴────────┐
                    │                 │
                    ↓                 ↓
         ┌──────────────────┐  ┌──────────────────┐
         │  LangChain Agent │  │  Direct Query    │
         │  (Conversational)│  │  (Summarize)     │
         └─────────┬────────┘  └────────┬─────────┘
                   │                    │
                   ↓                    ↓
         ┌──────────────────┐  ┌──────────────────┐
         │  Tool Selection  │  │  Get ALL Data    │
         │  & Execution     │  │  from Both DBs   │
         └─────────┬────────┘  └────────┬─────────┘
                   │                    │
                   ↓                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                              │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │   SQLite DB      │              │   ChromaDB       │         │
│  │  (Structured)    │              │  (Semantic)      │         │
│  │  sales_data      │              │  sales_insights  │         │
│  └──────────────────┘              └──────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Complete Data Flow

### Flow 1: Conversational Query (e.g., "What are top 5 products by sales?")

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: API Request                                                 │
└─────────────────────────────────────────────────────────────────────┘
User → POST /ask → {"question": "What are top 5 products by sales?"}
                    ↓
         FastAPI endpoint validates request
                    ↓
         Checks if data exists (get_data_info)
                    ↓
         Calls assistant.ask(question)

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Query Interpretation Agent                                  │
└─────────────────────────────────────────────────────────────────────┘
RetailInsightsAssistant.ask()
    ↓
Creates initial AgentState:
    {
        "user_query": "What are top 5 products by sales?",
        "query_intent": None,
        "data_source": None,
        "extracted_data": None,
        "response": None
    }
    ↓
Invokes LangGraph: self.graph.invoke(initial_state)
    ↓
AGENT 1: query_interpretation_agent(state)
    ↓
Sends to LLM with QUERY_CLASSIFICATION_PROMPT:
    "Analyze this query... return JSON"
    ↓
LLM (GeminiClient) analyzes query → Returns:
    {
        "query_type": "conversational",
        "intent": "answer",
        "confidence": 0.95
    }
    ↓
Updates state["query_intent"]

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Data Extraction Agent (Conversational Mode)                 │
└─────────────────────────────────────────────────────────────────────┘
AGENT 2: data_extraction_agent(state)
    ↓
Checks query_type: "conversational"
    ↓
Creates LangChain Agent:
    ↓
    1. Define tools:
       tools = [query_sqlite_tool, query_chromadb_tool]
    ↓
    2. Create LLM:
       llm_for_agent = ChatGoogleGenerativeAI(
           model="gemini-1.5-flash",
           temperature=0.3
       )
    ↓
    3. Create agent with prompt:
       agent = create_tool_calling_agent(
           llm=llm_for_agent,
           tools=tools,
           prompt=AGENT_PROMPT_TEMPLATE
       )
    ↓
    4. Create executor:
       executor = AgentExecutor(
           agent=agent,
           tools=tools,
           max_iterations=3,
           verbose=True
       )
    ↓
    5. Run agent:
       result = executor.invoke({"input": user_query})

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: LangChain Agent Reasoning & Tool Selection                  │
└─────────────────────────────────────────────────────────────────────┘
Agent receives:
    - System prompt: "You are a data exploration agent..."
    - Available tools: [query_sqlite_tool, query_chromadb_tool]
    - User query: "What are top 5 products by sales?"
    ↓
Agent's internal reasoning:
    "This is a structured data query requiring aggregation
     and ranking → I should use query_sqlite_tool"
    ↓
Agent decides to call: query_sqlite_tool

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: Tool Execution - query_sqlite_tool                          │
└─────────────────────────────────────────────────────────────────────┘
@tool
def query_sqlite_tool(query: str) -> str:
    ↓
    1. Get database schema:
       schema = get_sqlite_schema()
       → Returns: "Order ID, Product, Category, Quantity, Price, ..."
    ↓
    2. Generate SQL using LLM:
       sql_prompt = "Convert to SQL: {query} using schema: {schema}"
       ↓
       GeminiClient.generate(sql_prompt)
       ↓
       Returns SQL: "SELECT Product, SUM(Quantity * Price) as Total_Sales
                     FROM sales_data
                     GROUP BY Product
                     ORDER BY Total_Sales DESC
                     LIMIT 5"
    ↓
    3. Execute SQL query:
       execute_sqlite_query(sql)
       ↓
       SQLite connection → Executes query → Returns:
       {
           "success": True,
           "data": [
               {"Product": "Laptop", "Total_Sales": 150000},
               {"Product": "Phone", "Total_Sales": 120000},
               ...
           ],
           "rows": 5
       }
    ↓
    4. Format result:
       summary = "Found 5 records. Data: [...]"
       ↓
       Returns summary to agent

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 6: Agent Synthesizes Response                                  │
└─────────────────────────────────────────────────────────────────────┘
Agent receives tool result:
    "Found 5 records. Data: [Laptop: 150000, Phone: 120000, ...]"
    ↓
Agent synthesizes natural language response:
    "Based on the sales data, the top 5 products by sales are:
     1. Laptop - $150,000
     2. Phone - $120,000
     3. Tablet - $95,000
     4. Monitor - $80,000
     5. Keyboard - $65,000"
    ↓
Returns: {"output": "<response>", "intermediate_steps": [...]}

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 7: Response to User                                            │
└─────────────────────────────────────────────────────────────────────┘
data_extraction_agent completes:
    state["response"] = result.get("output")
    state["data_source"] = "langchain_agent"
    ↓
LangGraph pipeline completes
    ↓
assistant.ask() returns response
    ↓
FastAPI endpoint returns:
    {
        "response": "Based on the sales data...",
        "success": true
    }
    ↓
User receives answer
```

---

### Flow 2: Summarization Query (e.g., "Summarize all sales data")

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1-2: Same as Conversational (API → Query Interpretation)       │
└─────────────────────────────────────────────────────────────────────┘
User → GET /summarize
    ↓
LLM classifies as: {"query_type": "summarize"}

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Data Extraction Agent (Summarize Mode)                      │
└─────────────────────────────────────────────────────────────────────┘
data_extraction_agent(state)
    ↓
Checks query_type: "summarize"
    ↓
    1. Get ALL SQLite data:
       sql = "SELECT * FROM sales_data"
       sqlite_result = execute_sqlite_query(sql)
       → Returns: {rows: 10000, data: [...], ...}
    ↓
    2. Get ALL ChromaDB data:
       chromadb_result = retrieve_from_chromadb(
           "sales insights summary",
           n_results=20
       )
       → Returns: {documents: [...], metadatas: [...], ...}
       ↓
       formatted_context = format_rag_context(chromadb_result)
    ↓
    3. Combine data:
       combined_data = {
           "sqlite_records": 10000,
           "sqlite_preview": first_50_rows,
           "chromadb_context": formatted_context
       }
    ↓
    4. Generate comprehensive summary:
       prompt = FULL_DATA_SUMMARIZATION_PROMPT.format(
           sqlite_records=10000,
           sqlite_data=preview,
           chromadb_context=context
       )
       ↓
       response = llm.generate(prompt)
       ↓
       Returns: "Comprehensive summary covering:
                - 10,000 sales records
                - Key trends: ...
                - Insights from documents: ...
                - Recommendations: ..."
    ↓
    state["response"] = response
    state["data_source"] = "hybrid"
    ↓
Return to user
```

---

## Component Details

### 1. **main.py** - FastAPI Application

```python
# Entry point for HTTP requests

Endpoints:
├─ GET  /                    → Health check
├─ GET  /data-status         → Check if data is loaded
├─ POST /upload              → Upload CSV/Excel/JSON/TXT
├─ POST /ask                 → Ask a question (Q&A)
├─ GET  /summarize           → Generate summary
└─ GET  /data-info           → Get data statistics

Flow for /ask endpoint:
1. Validate request (QueryRequest model)
2. Check data exists: assistant.get_data_info()
3. Call: assistant.ask(question)
4. Return: QueryResponse(response, success)
```

### 2. **backend.py** - Core Agent Logic

#### 2.1 RetailInsightsAssistant Class

```python
class RetailInsightsAssistant:
    """Main orchestrator"""

    __init__():
        - Builds LangGraph state machine
        - Compiles agent pipeline

    get_data_info():
        - Queries SQLite for record count
        - Returns {total_records, columns}

    ask(question):
        - Creates initial state
        - Invokes graph.invoke(state)
        - Returns response

    summarize():
        - Pre-sets query_type = "summarize"
        - Invokes graph
        - Returns comprehensive summary
```

#### 2.2 Agent Pipeline

```python
LangGraph State Machine:
    Entry → query_interpretation_agent → data_extraction_agent → END

Agent 1: query_interpretation_agent
    Input: state with user_query
    Process:
        1. Send query to LLM with QUERY_CLASSIFICATION_PROMPT
        2. LLM returns JSON: {query_type, intent, confidence}
        3. Parse JSON using parse_json_response()
        4. Update state["query_intent"]
    Output: state with query_intent

Agent 2: data_extraction_agent
    Input: state with query_intent
    Branch based on query_type:

    IF query_type == "summarize":
        → Get ALL data from both databases
        → Combine and send to LLM
        → Return comprehensive summary

    ELSE (conversational):
        → Create LangChain agent
        → Agent selects and calls tools
        → Synthesize targeted answer

    Output: state with response
```

#### 2.3 LangChain Agent Components

```python
AGENT_PROMPT_TEMPLATE:
    System: "You are a data exploration agent..."
    Human: "{input}"
    Scratchpad: For agent's reasoning

Tools (decorated with @tool):
    1. query_sqlite_tool(query: str)
       - Generates SQL from natural language
       - Executes query
       - Returns formatted results

    2. query_chromadb_tool(query: str)
       - Retrieves semantic documents
       - Formats context
       - Returns relevant chunks

Agent Creation:
    llm = ChatGoogleGenerativeAI(...)
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent, tools, max_iterations=3)

Execution:
    result = executor.invoke({"input": user_query})
    → Agent autonomously:
        1. Reads system prompt
        2. Sees available tools
        3. Reasons about query
        4. Selects appropriate tool
        5. Calls tool
        6. Receives result
        7. Synthesizes answer
```

### 3. **tools.py** - Data Access Layer

```python
SQLite Functions:
├─ get_sqlite_connection()     → Returns DB connection
├─ execute_sqlite_query(sql)   → Runs SQL, returns results
├─ get_sqlite_schema()         → Returns column names
└─ ingest_csv_to_sqlite(df)    → Loads DataFrame to DB

ChromaDB Functions:
├─ get_chromadb_client()           → Returns client, collection, embedder
├─ retrieve_from_chromadb(query)   → Semantic search
├─ format_rag_context(results)     → Formats retrieved chunks
└─ ingest_to_chromadb(content)     → Embeds and stores documents

Tool Execution Flow:
    Tool called by agent
        ↓
    Accesses database (SQLite/ChromaDB)
        ↓
    Processes query
        ↓
    Returns formatted result string
        ↓
    Agent receives result
```

### 4. **utils.py** - LLM Client

```python
class GeminiClient:
    """Wrapper for Google Gemini API"""

    __init__():
        - Loads config (model, temperature, max_tokens)
        - Creates genai.Client

    generate(prompt: str) → str:
        - Sends prompt to Gemini
        - Returns text response

    generate_json(prompt: str) → dict:
        - Calls generate()
        - Parses JSON from response
        - Handles markdown code blocks
        - Returns dictionary

Usage:
    llm = GeminiClient()
    response = llm.generate("What is 2+2?")
    json_data = llm.generate_json("Return JSON: {...}")
```

### 5. **pydantic_models.py** - Data Models

```python
Models:
    QueryRequest:       {question: str}
    QueryResponse:      {response: str, success: bool}
    QueryPlan:          {query_type, intent, confidence}
    ValidationResult:   {is_valid, confidence, issues}
    AgentState:         {user_query, query_intent, data_source, ...}

Purpose:
    - Type validation
    - API contracts
    - State management in LangGraph
```

### 6. **prompt_template.py** - Prompts

```python
QUERY_CLASSIFICATION_PROMPT:
    "Analyze query → Return JSON: {query_type, intent, confidence}"

FULL_DATA_SUMMARIZATION_PROMPT:
    "Summarize all data from SQLite and ChromaDB
     Provide: insights, trends, recommendations"
```

---

## API Endpoints Flow

### POST /ask - Question Answering

```
Request: {"question": "Top 5 products?"}
    ↓
Validate request (QueryRequest model)
    ↓
Check data: get_data_info()
    ↓
If no data: Return error
    ↓
Else: assistant.ask(question)
    ↓
    [Agent Pipeline Executes]
    ↓
Return: {"response": "...", "success": true}
```

### GET /summarize - Data Summary

```
Request: GET /summarize
    ↓
Check data exists
    ↓
If no data: Return 400 error
    ↓
Else: assistant.summarize()
    ↓
Pre-creates state with query_type="summarize"
    ↓
    [Agent Pipeline - Summarize Mode]
    ↓
Return: {"summary": "...", "success": true}
```

### GET /data-status - Check Data

```
Request: GET /data-status
    ↓
assistant.get_data_info()
    ↓
Execute: SELECT COUNT(*) FROM sales_data
    ↓
Return: {
    "data_loaded": true/false,
    "total_records": 10000,
    "columns": [...],
    "message": "Database has 10,000 records"
}
```

### POST /upload - File Upload

```
Request: Multipart file upload
    ↓
Read file contents
    ↓
Branch by file type:

    CSV/Excel:
        → Read into DataFrame
        → ingest_csv_to_sqlite(df)
        → Return: {rows: N, pipeline: "sqlite"}

    JSON/TXT:
        → Extract text content
        → ingest_to_chromadb(content, metadata)
        → Return: {chunks: N, pipeline: "chromadb"}
```

---

## Tool Execution Flow

### query_sqlite_tool Flow

```
Agent calls: query_sqlite_tool("top 5 products by sales")
    ↓
1. Get schema:
   get_sqlite_schema() → "Order ID, Product, Category, ..."
    ↓
2. Generate SQL:
   LLM prompt: "Convert '{query}' to SQL using schema"
   → Returns: "SELECT Product, SUM(...) FROM sales_data ..."
    ↓
3. Execute SQL:
   execute_sqlite_query(sql)
   ↓
   SQLite connection
   ↓
   pd.read_sql_query(sql, conn)
   ↓
   Returns: {success: true, data: [...], rows: 5}
    ↓
4. Format response:
   "Found 5 records. Data: [{Product: 'Laptop', Sales: 150000}, ...]"
    ↓
Return to agent
```

### query_chromadb_tool Flow

```
Agent calls: query_chromadb_tool("customer insights")
    ↓
1. Get ChromaDB client:
   get_chromadb_client()
   → Returns: (client, collection, embedder)
    ↓
2. Generate query embedding:
   embedder.encode(["customer insights"])
   → Returns: [0.123, 0.456, ..., 0.789]
    ↓
3. Semantic search:
   collection.query(
       query_embeddings=[embedding],
       n_results=5
   )
   → Returns: {
       documents: ["insight 1", "insight 2", ...],
       metadatas: [{filename: "doc1"}, ...],
       distances: [0.12, 0.25, ...]
   }
    ↓
4. Format context:
   format_rag_context(results)
   ↓
   Creates formatted string:
   "=== RETRIEVED CONTEXT ===
    [Chunk 1] Source: doc1.txt
    Relevance: 0.88
    Content: ...
    --------------------------------------------------
    [Chunk 2] ..."
    ↓
5. Return to agent:
   "Found 5 relevant documents:\n{context}"
```

---

## Complete System Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           USER REQUEST                                    │
│  "What are the top 5 products by sales?"                                 │
└────────────────────────────┬─────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ API Layer (main.py)                                                    │
│  POST /ask → Validate → Check data → Call assistant.ask()             │
└────────────────────────────┬───────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ RetailInsightsAssistant (backend.py)                                   │
│  create initial_state → invoke graph.invoke(state)                     │
└────────────────────────────┬───────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ AGENT 1: query_interpretation_agent                                    │
│  ┌──────────────────────────────────────────────┐                      │
│  │ 1. Receive: user_query                       │                      │
│  │ 2. LLM classifies query                      │                      │
│  │ 3. Returns: {query_type: "conversational"}   │                      │
│  │ 4. Update state["query_intent"]              │                      │
│  └──────────────────────────────────────────────┘                      │
└────────────────────────────┬───────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ AGENT 2: data_extraction_agent                                         │
│  ┌──────────────────────────────────────────────┐                      │
│  │ Check query_type:                            │                      │
│  │   IF "summarize" → Get ALL data              │                      │
│  │   ELSE → Create LangChain agent              │                      │
│  └──────────────────┬───────────────────────────┘                      │
│                     ↓                                                   │
│  ┌──────────────────────────────────────────────┐                      │
│  │ LangChain Agent Setup:                       │                      │
│  │ 1. tools = [query_sqlite_tool,              │                      │
│  │             query_chromadb_tool]             │                      │
│  │ 2. llm = ChatGoogleGenerativeAI()           │                      │
│  │ 3. agent = create_tool_calling_agent(...)   │                      │
│  │ 4. executor = AgentExecutor(...)            │                      │
│  └──────────────────┬───────────────────────────┘                      │
│                     ↓                                                   │
│  ┌──────────────────────────────────────────────┐                      │
│  │ executor.invoke({"input": user_query})       │                      │
│  └──────────────────┬───────────────────────────┘                      │
└────────────────────┬┴───────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────────────────────┐
│ LangChain Agent Reasoning                                              │
│  ┌──────────────────────────────────────────────┐                      │
│  │ Agent receives:                              │                      │
│  │ - System: "You are a data exploration agent" │                      │
│  │ - Tools: [query_sqlite_tool, ...]           │                      │
│  │ - Input: "Top 5 products by sales?"         │                      │
│  └──────────────────┬───────────────────────────┘                      │
│                     ↓                                                   │
│  ┌──────────────────────────────────────────────┐                      │
│  │ Agent reasons:                               │                      │
│  │ "This is structured query → use SQLite tool" │                      │
│  └──────────────────┬───────────────────────────┘                      │
│                     ↓                                                   │
│  ┌──────────────────────────────────────────────┐                      │
│  │ Calls: query_sqlite_tool(...)                │                      │
│  └──────────────────┬───────────────────────────┘                      │
└────────────────────┬┴───────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────────────────────┐
│ query_sqlite_tool Execution                                            │
│  ┌──────────────────────────────────────────────┐                      │
│  │ 1. get_sqlite_schema() → columns             │                      │
│  │ 2. LLM generates SQL from NL query           │                      │
│  │ 3. execute_sqlite_query(sql)                 │                      │
│  │    ↓                                         │                      │
│  │   SQLite DB → Returns results                │                      │
│  │ 4. Format: "Found 5 records. Data: [...]"   │                      │
│  └──────────────────┬───────────────────────────┘                      │
└────────────────────┬┴───────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Agent Synthesizes Response                                             │
│  ┌──────────────────────────────────────────────┐                      │
│  │ Receives tool result                         │                      │
│  │ ↓                                            │                      │
│  │ Generates natural language response:         │                      │
│  │ "Top 5 products by sales are:               │                      │
│  │  1. Laptop - $150,000                       │                      │
│  │  2. Phone - $120,000..."                    │                      │
│  └──────────────────┬───────────────────────────┘                      │
└────────────────────┬┴───────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Back to Pipeline                                                       │
│  state["response"] = agent_output                                      │
│  state["data_source"] = "langchain_agent"                              │
└────────────────────────────┬───────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Return to User                                                         │
│  FastAPI → {"response": "...", "success": true}                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **Separation of Concerns**:
   - `main.py`: HTTP interface
   - `backend.py`: Agent logic
   - `tools.py`: Data access
   - `utils.py`: LLM client

2. **Agent Autonomy**:
   - LangChain agent decides which tool to use
   - No hardcoded routing for conversational queries
   - Agent can use multiple tools if needed

3. **Two Query Modes**:
   - **Summarize**: Gets ALL data from both databases
   - **Conversational**: Targeted retrieval via agent

4. **Data Sources**:
   - **SQLite**: Structured sales data (fast SQL queries)
   - **ChromaDB**: Semantic documents (embedding-based search)

5. **LangGraph Pipeline**:
   - State flows through agents
   - Each agent enriches the state
   - Final state contains the response

---

## File Reference Map

```
main.py
├─ Defines API endpoints
├─ Imports: RetailInsightsAssistant from backend
├─ Imports: Data ingestion tools from tools
└─ Returns responses to users

backend.py
├─ RetailInsightsAssistant class
├─ Agent functions (query_interpretation, data_extraction)
├─ LangChain agent setup
├─ Tool definitions with @tool decorator
├─ Imports: GeminiClient from utils
├─ Imports: Tools from tools
└─ Imports: Prompts from prompt_template

tools.py
├─ SQLite functions (connection, schema, query)
├─ ChromaDB functions (retrieval, formatting)
├─ Data ingestion functions
└─ Tool registry

utils.py
├─ GeminiClient (LLM wrapper)
├─ JSON parsing utilities
└─ DataFrame formatting

pydantic_models.py
├─ Request/Response models
├─ Agent state definition
└─ Validation models

prompt_template.py
├─ Query classification prompt
└─ Summarization prompt

config.py
└─ API keys, LLM config, paths
```
