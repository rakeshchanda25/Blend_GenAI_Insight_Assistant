### Important Libraries Import ###
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from pydantic_models import QueryRequest, QueryResponse
from tools import ingest_csv_to_sqlite, ingest_to_chromadb
from backend import RetailInsightsAssistant

app = FastAPI(title="Blend - Retail Insights Assistant API", version="1.0.0")

# Initialize the assistant
assistant = RetailInsightsAssistant()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

###################### API Endpoints #######################################3
@app.get("/")
def root():
    return {"message": "Blend - Retail Insights Assistant API", "status": "running"}

@app.get("/data-status")
def data_status():
    """Check current data loading status and get data info."""
    try:
        info = assistant.get_data_info()
        total_records = info.get('total_records', 0)
        columns = info.get('columns', [])

        return {
            "success": True,
            "data_loaded": total_records > 0,
            "total_records": total_records,
            "columns": columns,
            "message": f"Database has {total_records:,} records" if total_records > 0 else "No data loaded yet"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload CSV/Excel/JSON/TXT file with dual pipeline routing."""
    try:
        contents = await file.read()

        # PIPELINE 1: Structured data (CSV/Excel) → SQLite
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
            result = ingest_csv_to_sqlite(df, table_name="sales_data")
            # Also load to assistant for backward compatibility
            assistant.load_data([df])
            return {
                "success": result["success"],
                "pipeline": "sqlite",
                "filename": file.filename,
                "rows": result.get("rows", len(df)),
                "message": result.get("message", "")
            }

        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
            result = ingest_csv_to_sqlite(df, table_name="sales_data")
            # Also load to assistant for backward compatibility
            assistant.load_data([df])
            return {
                "success": result["success"],
                "pipeline": "sqlite",
                "filename": file.filename,
                "rows": result.get("rows", len(df)),
                "message": result.get("message", "")
            }

        # PIPELINE 2: Unstructured/summarized docs (JSON/TXT) → ChromaDB
        elif file.filename.endswith('.json'):
            import json
            data = json.loads(contents.decode('utf-8'))

            # Convert to text for RAG ingestion
            if isinstance(data, list):
                content = "\n\n".join([str(item) for item in data])
            else:
                content = str(data)

            metadata = {
                'filename': file.filename,
                'doc_type': 'json_summary',
                'doc_id': f"json_{file.filename}"
            }

            result = ingest_to_chromadb(content, metadata)
            return {
                "success": result["success"],
                "pipeline": "chromadb",
                "filename": file.filename,
                "chunks": result.get("chunks", 0),
                "message": result.get("message", "")
            }

        elif file.filename.endswith('.txt'):
            content = contents.decode('utf-8')

            metadata = {
                'filename': file.filename,
                'doc_type': 'text_summary',
                'doc_id': f"txt_{file.filename}"
            }

            result = ingest_to_chromadb(content, metadata)
            return {
                "success": result["success"],
                "pipeline": "chromadb",
                "filename": file.filename,
                "chunks": result.get("chunks", 0),
                "message": result.get("message", "")
            }

        else:
            raise HTTPException(status_code=400, detail="Supported: CSV, Excel, JSON, TXT")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    """Ask a question (Q&A mode)."""
    info = assistant.get_data_info()
    if info.get("total_records", 0) == 0:
        return QueryResponse(response="No data loaded. Please load data to SQLite/ChromaDB first.", success=False)

    try:
        response = assistant.ask(request.question)
        return QueryResponse(response=response, success=True)
    except Exception as e:
        return QueryResponse(response=f"Error: {str(e)}", success=False)


@app.get("/summarize")
def get_summary():
    """Generate data summary (Summarization mode)."""
    info = assistant.get_data_info()
    if info.get("total_records", 0) == 0:
        raise HTTPException(status_code=400, detail="No data loaded. Please load data to SQLite/ChromaDB first.")

    try:
        summary = assistant.summarize()
        return {"summary": summary, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data-info")
def get_data_info():
    """Get data information."""
    info = assistant.get_data_info()
    return {
        "data_loaded": info.get("total_records", 0) > 0,
        "total_records": info.get("total_records", 0),
        "columns": info.get("columns", [])
    }

### Main Defination ###
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
