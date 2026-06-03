# 🛍️ Retail Insights Assistant

AI-powered retail analytics assistant using LangGraph agents, ChromaDB, and Google Gemini LLM for intelligent sales data analysis.

---

## 📋 Overview

**Retail Insights Assistant** is an intelligent analytics platform that combines:
- **Natural Language Queries**: Ask questions in plain English about your sales data
- **Multi-Agent Architecture**: Specialized agents for query interpretation, data extraction, and validation
- **Hybrid Data Sources**: SQL databases for structured data + ChromaDB for semantic insights
- **Security Validation**: Built-in SQL injection detection and response quality validation

### Key Features

✅ **Smart Query Processing**
- Automatically classifies queries (conversational vs. summarization)
- Routes to appropriate data sources (SQL, vector DB, or hybrid)
- Uses LangChain agents with autonomous tool selection

✅ **Data Security**
- SQL injection pattern detection (blacklist + whitelist)
- Response validation for relevance and quality
- Read-only database access

✅ **Flexible Data Ingestion**
- Upload CSV or Excel files
- Automatic ingestion to SQLite (structured queries)
- ChromaDB vectorization (semantic search)

✅ **Interactive UI**
- Modern Streamlit interface
- Chat-based interaction
- Real-time status monitoring

---

## 🚀 Quick Start

### Prerequisites

- **Option 1 (Docker)**: Docker & Docker Compose installed
- **Option 2 (Manual)**: Python 3.9+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

---

### 🐳 Docker Setup (Recommended)

**Easiest way to run the application with zero dependency issues!**

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Blend_Assignment
   ```

2. **Configure API key**
   ```bash
   # Copy environment template
   cp .env.example .env

   # Edit .env and add your GEMINI_API_KEY
   nano .env  # or use any text editor
   ```

3. **Configure backend**
   ```bash
   # Copy config template
   cp BACKEND/config.example.py BACKEND/config.py

   # Edit config.py and add your GEMINI_API_KEY
   nano BACKEND/config.py
   ```

4. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

5. **Access the application**
   - Frontend UI: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

6. **Stop the application**
   ```bash
   docker-compose down
   ```

**Docker commands:**
```bash
# Run in detached mode (background)
docker-compose up -d

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up --build

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes
docker-compose down -v
```

---

### 💻 Manual Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Blend_Assignment
   ```

2. **Install dependencies**
   ```bash
   # Backend
   cd BACKEND
   pip install -r requirements.txt

   # Frontend
   cd ../FRONTEND
   pip install -r requirements.txt
   ```

3. **Configure API keys**
   ```bash
   # In BACKEND directory
   cp config.example.py config.py
   # Edit config.py and add your GEMINI_API_KEY
   ```

4. **Run the application**

   **Terminal 1 - Backend API:**
   ```bash
   cd BACKEND
   python main.py
   # API runs on http://localhost:8000
   ```

   **Terminal 2 - Frontend UI:**
   ```bash
   cd FRONTEND
   streamlit run app.py
   # UI opens at http://localhost:8501
   ```

5. **Upload data & start querying**
   - Upload a CSV/Excel file via the sidebar
   - Ask questions like: "What are the top 5 products by sales?"
   - Get instant AI-powered insights

---

## 💡 Usage Examples

### Conversational Queries
```
"Top 5 regions by revenue"
"Show products with sales above $10,000"
"Average order value by customer segment"
```

### Summarization
```
"Generate a comprehensive summary"
"Overall sales trends"
```

### Insights
```
"What insights can you provide about customer behavior?"
"Analyze sales patterns"
```

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                      │
│  • File upload UI                                            │
│  • Chat interface                                            │
│  • Real-time status monitoring                               │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         LangGraph Agent Pipeline                       │ │
│  │                                                        │ │
│  │  ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │ │
│  │  │   Agent 1:   │───▶│   Agent 2:   │───▶│ Agent 3:│ │ │
│  │  │    Query     │    │     Data     │    │ Validator│ │ │
│  │  │Interpretation│    │  Extraction  │    │         │ │ │
│  │  └──────────────┘    └──────────────┘    └─────────┘ │ │
│  │         │                    │                  │     │ │
│  │         ▼                    ▼                  ▼     │ │
│  │   Classify query      LangChain Agent    Validate:   │ │
│  │   (summarize vs.      with tools:        • Security  │ │
│  │    conversational)    • query_sqlite     • Relevance │ │
│  │                       • query_chromadb   • Quality   │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────┬────────────────────┬────────────────────────┘
                │                    │
       ┌────────▼────────┐  ┌────────▼────────┐
       │   SQLite DB     │  │   ChromaDB      │
       │  (Structured)   │  │   (Semantic)    │
       └─────────────────┘  └─────────────────┘
```

### Agent Pipeline

**Agent 1: Query Interpretation**
- Classifies query type using LLM
- Returns: `{query_type: "summarize"|"conversational", intent, confidence}`

**Agent 2: Data Extraction**
- **Summarization Mode**: Fetches ALL data from SQLite + ChromaDB
- **Conversational Mode**: Uses LangChain agent with tool selection
  - Tools: `query_sqlite_tool`, `query_chromadb_tool`
  - Agent autonomously decides which tool(s) to use
- Generates natural language response

**Agent 3: Validator**
- **SQL Security Check**: Detects injection patterns (blacklist + whitelist)
- **LLM Validation**: Checks response relevance and quality
- **Failure Handling**: Blocks security issues, warns on quality issues

### Data Flow

1. **Upload** → CSV/Excel file
2. **Ingestion** → SQLite (structured) + ChromaDB (vectorized)
3. **Query** → User asks natural language question
4. **Interpretation** → Classify query type
5. **Extraction** → Retrieve data via SQL or semantic search
6. **Validation** → Security + quality checks
7. **Response** → Return validated answer to user

---

## 🔧 Technical Details

### Backend Stack
- **Framework**: FastAPI
- **Agent Orchestration**: LangGraph (StateGraph)
- **LLM**: Google Gemini (gemini-1.5-flash)
- **Databases**:
  - SQLite (structured queries)
  - ChromaDB (vector similarity search)
- **Embeddings**: SentenceTransformer (`all-MiniLM-L6-v2`)
- **Agent Framework**: LangChain with tool-calling

### Frontend Stack
- **Framework**: Streamlit
- **Styling**: Custom CSS with gradient UI
- **API Communication**: Python requests
- **Timeout**: 10 minutes for long-running queries

### Security Features

**SQL Injection Detection**
- Blacklist patterns: DROP, DELETE, UNION, comments, system tables
- Whitelist validation: Only SELECT on `sales_data` table
- Automatic query blocking on security violations

**Response Validation**
- Relevance scoring (does it answer the question?)
- Quality scoring (accuracy, completeness)
- Confidence thresholds

### Project Structure

```
Blend_Assignment/
├── BACKEND/
│   ├── main.py                 # FastAPI server
│   ├── backend.py              # LangGraph agents
│   ├── tools.py                # Tool definitions (SQLite, ChromaDB)
│   ├── utils.py                # LLM client, SQL injection detection
│   ├── prompt_template.py      # LLM prompts
│   ├── pydantic_models.py      # State & response models
│   ├── config.py               # API keys (NOT in git)
│   ├── config.example.py       # Config template
│   └── requirements.txt
├── FRONTEND/
│   ├── app.py                  # Streamlit UI
│   └── requirements.txt
├── data/                       # Auto-generated
│   ├── sales.db               # SQLite database
│   └── chroma/                # ChromaDB vector store
└── README.md
```

---

## 🔐 Configuration

### Backend (`BACKEND/config.py`)

```python
GEMINI_API_KEY = "your-api-key-here"

LLM_CONFIG = {
    "model": "gemini-1.5-flash",
    "temperature": 0.3,
    "max_tokens": 2048
}
```

### Environment Variables (optional)
```bash
export GEMINI_API_KEY="your-key"
export API_BASE_URL="http://localhost:8000"
```

---

## 📊 API Endpoints

### Health Check
```http
GET /
Response: {"status": "ok", "message": "Retail Insights API"}
```

### Data Status
```http
GET /data-status
Response: {
  "data_loaded": true,
  "total_records": 1000,
  "columns": ["product", "sales", "region", ...]
}
```

### File Upload
```http
POST /upload
Content-Type: multipart/form-data
Body: file (CSV/Excel)
Response: {"success": true, "rows": 1000}
```

### Ask Question
```http
POST /ask
Content-Type: application/json
Body: {"question": "Top 5 products by sales?"}
Response: {"success": true, "response": "..."}
```

### Generate Summary
```http
GET /summarize
Response: {"success": true, "summary": "..."}
```

---

## 🧪 Testing

### Test SQL Injection Detection
```python
# Should be blocked
POST /ask
{
  "question": "Show data; DROP TABLE sales_data"
}
# Response: Security validation error
```

### Test Normal Query
```python
POST /ask
{
  "question": "Top 5 regions by revenue"
}
# Response: Valid data analysis
```

---

## 🐛 Troubleshooting

### Issue: "API Offline" in frontend
- Check backend is running on port 8000
- Verify `API_BASE_URL` in frontend

### Issue: "No data loaded"
- Upload a CSV/Excel file via sidebar
- Check file format (must have headers)

### Issue: Timeout errors
- Increase timeout in `FRONTEND/app.py` (currently 600s)
- Reduce data size or optimize query

### Issue: LLM errors
- Verify `GEMINI_API_KEY` in `BACKEND/config.py`
- Check API quota/limits

---

## 📈 Performance Notes

- **SQLite**: Handles 100K+ rows efficiently
- **ChromaDB**: HNSW indexing for fast vector search
- **LLM**: Uses gemini-1.5-flash for speed/cost balance
- **Timeout**: 10 minutes for complex queries

---

## 🚧 Known Limitations

- Single-user design (no concurrent session handling)
- In-memory ChromaDB (data persists but not optimized for large scale)
- No authentication/authorization
- Limited to single CSV upload (overwrites previous data)

---

## 🛣️ Future Enhancements

- [ ] Multi-user support with session management
- [ ] Data persistence across restarts
- [ ] Support for multiple datasets
- [ ] Advanced visualizations (charts, graphs)
- [ ] Export results to CSV/PDF
- [ ] User authentication
- [ ] Query history and favorites
- [ ] Real-time streaming responses

---

## 📝 License

MIT License - see LICENSE file for details

---

## 👥 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📧 Support

For issues or questions:
- Open a GitHub issue
- Contact: [your-email@example.com]

---

## 🙏 Acknowledgments

- **LangGraph**: Agent orchestration framework
- **Google Gemini**: LLM API
- **ChromaDB**: Vector database
- **Streamlit**: Rapid UI development
- **FastAPI**: Modern Python web framework

---

**Built with ❤️ for intelligent retail analytics**
