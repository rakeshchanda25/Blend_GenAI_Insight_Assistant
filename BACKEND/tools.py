import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer
import logging
from config import DATA_DIR
from pathlib import Path
import sqlite3
from langchain_core.tools import tool
from utils import GeminiClient

# Database path
_db_path = "data/sales.db"

logger = logging.getLogger(__name__)

# LLM client for SQL generation
llm = GeminiClient()

# Track last generated SQL for security validation (shared with backend.py)
_last_generated_sql = None

def get_last_generated_sql():
    """Get the last generated SQL for validation."""
    global _last_generated_sql
    return _last_generated_sql

def reset_last_generated_sql():
    """Reset the last generated SQL tracker."""
    global _last_generated_sql
    _last_generated_sql = None

############ SQLITE QUERY FUNCTIONS ###########

def get_sqlite_connection():
    """Get or create SQLite connection (internal utility)."""
    Path("data").mkdir(exist_ok=True)
    # Create fresh connection each time to avoid caching issues
    conn = sqlite3.connect(_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@tool
def execute_sqlite_query(sql: str) -> dict:
    """
    Execute SQL query on SQLite database.

    Args:
        sql: SQL query string

    Returns:
        dict: {"success": bool, "data": list, "rows": int, "preview": str}
    """
    try:
        conn = get_sqlite_connection()
        result_df = pd.read_sql_query(sql, conn)

        # # Create preview
        # preview_lines = []
        # for _, row in result_df.head(10).iterrows():
        #     preview_lines.append(" | ".join(str(v) for v in row))

        # preview = "\n".join(preview_lines)
        # if len(result_df) > 10:
        #     preview += f"\n... and {len(result_df) - 10} more rows"

        logger.info(f"SQLite query returned {len(result_df)} rows")

        return {
            "success": True,
            "data": result_df.to_dict(orient="records"),
            "columns": result_df.columns.tolist(),
            "rows": len(result_df),
        }
    except Exception as e:
        logger.error(f"SQLite query error: {e}\nSQL: {sql}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "rows": 0
        }

@tool
def get_sqlite_schema() -> str:
    """Get list of columns in sales_data table."""
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sales_data)")
        columns = [row[1] for row in cursor.fetchall()]
        return ", ".join(columns)
    except:
        return ""

@tool
def query_sqlite_tool(query: str) -> str:
    """Query structured sales data using SQL.

    Args:
        query: Natural language description of what data you need

    Returns:
        Retrieved data summary with row count and sample data

    Use this for: aggregations, rankings, filters, comparisons, specific metrics
    Example: "get top 5 products by sales" or "total revenue by region"
    """
    global _last_generated_sql
    try:
        # Generate SQL from natural language query (use .invoke() for @tool decorated functions)
        schema = get_sqlite_schema.invoke({})
        sql_prompt = f"""Convert this request to SQLite SQL query.

Request: {query}
Table: sales_data
Columns: {schema}

Rules:
- Output ONLY the SQL query, no markdown, no explanation
- Use SQLite syntax (not MySQL or PostgreSQL)
- Query the 'sales_data' table

SQL:"""

        sql = llm.generate(sql_prompt).strip()
        sql = clean_sql(sql)  # Remove markdown formatting
        logger.info(f"Generated SQL: {sql[:100]}...")

        # Track SQL for security validation
        _last_generated_sql = sql

        # Execute SQL (use .invoke() for @tool decorated functions)
        result = execute_sqlite_query.invoke({"sql": sql})

        if result.get("success"):
            data = result.get("data", [])
            rows = result.get("rows", 0)
            summary = f"Found {rows} records. Data: {str(data[:10])}..."  # Show first 10 rows
            return summary
        else:
            error = result.get("error", "Query failed")
            return f"SQL query failed: {error}"

    except Exception as e:
        logger.error(f"SQLite tool error: {e}")
        return f"Error querying SQLite: {str(e)}"


@tool
def query_chromadb_tool(query: str) -> str:
    """Query semantic documents and insights from ChromaDB.

    Args:
        query: Question or topic to search for

    Returns:
        Retrieved documents with relevance scores

    Use this for: insights, recommendations, analysis, explanations
    Example: "customer behavior insights" or "sales trends analysis"
    """
    try:
        # Retrieve relevant chunks (use .invoke() for @tool decorated functions)
        result = retrieve_from_chromadb.invoke({"query": query, "n_results": 5})

        if result.get("success") and result.get("documents"):
            context = format_rag_context.invoke({"rag_results": result})
            return f"Found {result.get('count', 0)} relevant documents:\n{context[:1000]}..."
        else:
            return "No relevant documents found for this query."

    except Exception as e:
        logger.error(f"ChromaDB tool error: {e}")
        return f"Error querying ChromaDB: {str(e)}"

def clean_sql(sql: str) -> str:
    """Remove markdown code blocks and clean SQL."""
    import re
    # Remove ```sql ... ``` or ``` ... ``` blocks
    sql = re.sub(r'```sql\s*', '', sql)
    sql = re.sub(r'```\s*', '', sql)
    sql = sql.strip()
    # Remove any trailing semicolons and whitespace
    while sql.endswith(';'):
        sql = sql[:-1].strip()
    return sql + ';' if sql else sql

################# CHROMADB RETRIEVAL FUNCTIONS ######################

# Global ChromaDB client and collection
_chroma_path = "data/chroma"
_client = None
_collection = None
_embedder = None

def get_chromadb_client():
    """Get or create ChromaDB client with collection and embedder."""
    global _client, _collection, _embedder

    if _client is None:
        Path(_chroma_path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=_chroma_path)

        # Create collection with HNSW settings
        _collection = _client.get_or_create_collection(
            name="sales_insights",
            metadata={
                "hnsw:space": "cosine",
                "hnsw:construction_ef": 100,
                "hnsw:search_ef": 50,
                "hnsw:M": 16
            }
        )

        # Initialize embedder
        _embedder = SentenceTransformer('all-MiniLM-L6-v2')

    return _client, _collection, _embedder

@tool
def retrieve_from_chromadb(query: str, n_results: int = 5, filters: dict = None) -> dict:
    """
    RAG retrieval with metadata filtering.

    Args:
        query: User query
        n_results: Number of chunks to retrieve
        filters: Metadata filters

    Returns:
        Dictionary with documents, metadatas, and distances
    """
    try:
        _, collection, embedder = get_chromadb_client()

        # Generate query embedding
        query_embedding = embedder.encode([query], show_progress_bar=False)[0].tolist()

        # Build where clause for filtering
        where_clause = None
        if filters:
            where_clause = {}
            for key, value in filters.items():
                if isinstance(value, dict):
                    where_clause[key] = value
                else:
                    where_clause[key] = {"$eq": value}

        # Retrieve with filters
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause if where_clause else None
        )

        # Format results
        if results and results['documents'] and results['documents'][0]:
            return {
                "success": True,
                "documents": results['documents'][0],
                "metadatas": results['metadatas'][0],
                "distances": results['distances'][0],
                "count": len(results['documents'][0])
            }
        else:
            return {
                "success": True,
                "documents": [],
                "metadatas": [],
                "distances": [],
                "count": 0
            }

    except Exception as e:
        logger.error(f"ChromaDB retrieval error: {e}")
        return {
            "success": False,
            "documents": [],
            "metadatas": [],
            "distances": [],
            "count": 0,
            "error": str(e)
        }


@tool
def format_rag_context(rag_results: dict) -> str:
    """Format retrieved chunks for LLM context."""
    if not rag_results.get("success") or not rag_results.get("documents"):
        return ""

    documents = rag_results["documents"]
    metadatas = rag_results.get("metadatas", [])
    distances = rag_results.get("distances", [])

    context_parts = ["=== RETRIEVED CONTEXT FROM DOCUMENTS ===\n"]

    for i, doc in enumerate(documents):
        context_parts.append(f"\n[Chunk {i+1}]")

        if i < len(metadatas):
            meta = metadatas[i]
            if 'filename' in meta:
                context_parts.append(f"Source: {meta['filename']}")
            if 'doc_type' in meta:
                context_parts.append(f"Type: {meta['doc_type']}")
            if i < len(distances):
                context_parts.append(f"Relevance: {1 - distances[i]:.2f}")

        context_parts.append(f"\n{doc}\n")
        context_parts.append("-" * 50)

    return "\n".join(context_parts)

# ============= DATA INGESTION FUNCTIONS =============

def ingest_csv_to_sqlite(df: pd.DataFrame, table_name: str = "sales_data") -> dict:
    """Ingest DataFrame into SQLite database."""
    try:
        conn = get_sqlite_connection()
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        logger.info(f"Ingested {len(df)} rows into SQLite table '{table_name}'")
        return {
            "success": True,
            "message": f"Successfully ingested {len(df)} rows",
            "rows": len(df),
            "table_name": table_name,
            "columns": df.columns.tolist()
        }
    except Exception as e:
        logger.error(f"CSV ingestion error: {e}")
        return {
            "success": False,
            "message": f"Failed to ingest CSV: {str(e)}",
            "error": str(e),
            "rows": 0
        }


def ingest_to_chromadb(content: str, metadata: dict = None, chunk_size: int = 500) -> dict:
    """Ingest text content into ChromaDB with semantic chunking."""
    try:
        _, collection, embedder = get_chromadb_client()
        if len(content) > chunk_size:
            chunks = content.split('\n\n')
            if len(chunks) == 1:
                chunks = content.split('\n')
            if len(chunks) == 1:
                chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        else:
            chunks = [content]

        chunks = [c.strip() for c in chunks if c.strip()]

        if not chunks:
            return {"success": False, "message": "No content to ingest", "chunks": 0}

        embeddings = embedder.encode(chunks, show_progress_bar=False).tolist()

        chunk_metadata = []
        for i in range(len(chunks)):
            meta = metadata.copy() if metadata else {}
            meta['chunk_index'] = i
            meta['chunk_count'] = len(chunks)
            chunk_metadata.append(meta)

        chunk_ids = [
            f"{metadata.get('doc_id', 'unknown')}_{i}" for i, _ in enumerate(chunks)
        ] if metadata and 'doc_id' in metadata else [f"chunk_{i}" for i in range(len(chunks))]

        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=chunk_metadata,
            ids=chunk_ids
        )

        logger.info(f"Ingested {len(chunks)} chunks into ChromaDB")
        return {
            "success": True,
            "message": f"Successfully ingested {len(chunks)} chunks",
            "chunks": len(chunks),
            "doc_id": metadata.get('doc_id', 'unknown') if metadata else 'unknown'
        }
    except Exception as e:
        logger.error(f"ChromaDB ingestion error: {e}")
        return {
            "success": False,
            "message": f"Failed to ingest to ChromaDB: {str(e)}",
            "error": str(e),
            "chunks": 0
        }


# ============= TOOL REGISTRY =============

# TOOLS = {
#     "execute_sqlite_query": execute_sqlite_query,
#     "get_sqlite_schema": get_sqlite_schema,
#     "retrieve_from_chromadb": retrieve_from_chromadb,
#     "format_rag_context": format_rag_context
# }

