################### Libraries Import ######################
from typing import TypedDict, Optional, Any
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    response: str
    success: bool

class QueryPlan(BaseModel):
    """Parsed query plan from interpretation agent."""
    query_type: str = Field(description="summarize/converstaional")
    intent: str = Field(description="summarize/answer")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

class ValidationResult(BaseModel):
    """Result of query validation."""
    is_valid: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)

class AgentState(TypedDict):
    """State passed between agent functions in the graph."""
    user_query: str
    query_intent: Optional[dict]
    data_source: Optional[str]
    extracted_data: Optional[dict]
    response: Optional[str]
    error: Optional[str]
    metadata: Optional[dict]
    # Validation fields
    validation_result: Optional[dict]  # Stores ValidationResult as dict
    generated_sql: Optional[str]       # Track SQL for security validation
    is_validated: Optional[bool]       # Quick check if validation passed
