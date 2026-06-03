# 🐳 Docker Setup Guide

Complete guide for running Retail Insights Assistant using Docker.

---

## Prerequisites

- Docker 20.10+ installed ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ installed ([Install Docker Compose](https://docs.docker.com/compose/install/))
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

---

## Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Blend_Assignment
```

### 2. Set Up Environment Variables

Create `.env` file from template:
```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```env
GEMINI_API_KEY=your-actual-api-key-here
API_BASE_URL=http://backend:8000
```

### 3. Set Up Backend Configuration

Create config file from template:
```bash
cp BACKEND/config.example.py BACKEND/config.py
```

Edit `BACKEND/config.py`:
```python
GEMINI_API_KEY = "your-actual-api-key-here"

LLM_CONFIG = {
    "model": "gemini-1.5-flash",
    "temperature": 0.3,
    "max_tokens": 2048
}
```

### 4. Build and Run

```bash
docker-compose up --build
```

Wait for the build to complete. You'll see:
```
retail-insights-backend  | INFO:     Application startup complete.
retail-insights-frontend | You can now view your Streamlit app in your browser.
```

### 5. Access the Application

- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## Docker Compose Services

The application consists of two services:

### Backend Service
- **Port**: 8000
- **Container**: `retail-insights-backend`
- **Built from**: `./BACKEND/Dockerfile`
- **Volumes**:
  - `./data:/app/data` - Data persistence
  - `./BACKEND/config.py:/app/config.py` - Configuration

### Frontend Service
- **Port**: 8501
- **Container**: `retail-insights-frontend`
- **Built from**: `./FRONTEND/Dockerfile`
- **Depends on**: backend service
- **Environment**: Uses backend service URL

---

## Common Commands

### Start Services
```bash
# Start in foreground (see logs)
docker-compose up

# Start in background (detached mode)
docker-compose up -d

# Build and start
docker-compose up --build
```

### Stop Services
```bash
# Stop containers (keep data)
docker-compose down

# Stop and remove volumes (delete data)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100
```

### Rebuild Services
```bash
# Rebuild all services
docker-compose build

# Rebuild specific service
docker-compose build backend
docker-compose build frontend

# Rebuild without cache
docker-compose build --no-cache
```

### Execute Commands in Containers
```bash
# Open bash in backend container
docker-compose exec backend bash

# Open bash in frontend container
docker-compose exec frontend bash

# Run Python command in backend
docker-compose exec backend python -c "import sys; print(sys.version)"
```

---

## File Structure

```
Blend_Assignment/
├── docker-compose.yml          # Orchestrates both services
├── .env                        # Environment variables (not in git)
├── .env.example               # Environment template
├── .dockerignore              # Files to exclude from Docker build
│
├── BACKEND/
│   ├── Dockerfile             # Backend container definition
│   ├── requirements.txt       # Python dependencies
│   ├── config.py             # API keys (not in git)
│   ├── config.example.py     # Config template
│   └── ...                   # Application code
│
├── FRONTEND/
│   ├── Dockerfile            # Frontend container definition
│   ├── requirements.txt      # Python dependencies
│   └── app.py               # Streamlit application
│
└── data/                     # Mounted volume for persistence
    ├── sales.db             # SQLite database
    └── chroma/              # ChromaDB vector store
```

---

## Environment Variables

### Backend (.env file)
```env
# Required
GEMINI_API_KEY=your-key-here

# Optional
LLM_MODEL=gemini-1.5-flash
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048
DB_PATH=data/sales.db
CHROMA_PATH=data/chroma
```

### Frontend
```env
API_BASE_URL=http://backend:8000
```

---

## Data Persistence

Docker volumes ensure data persists across container restarts:

### SQLite Database
- **Location**: `./data/sales.db`
- **Mounted to**: `/app/data/sales.db` in backend container
- **Contains**: Uploaded CSV data

### ChromaDB Vector Store
- **Location**: `./data/chroma/`
- **Mounted to**: `/app/data/chroma/` in backend container
- **Contains**: Vectorized embeddings for semantic search

### Clearing Data
```bash
# Remove all data
rm -rf data/

# Or use Docker Compose
docker-compose down -v
```

---

## Troubleshooting

### Issue: Port already in use
```bash
# Check what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change ports in docker-compose.yml
```

### Issue: Permission denied (Linux)
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
```

### Issue: API key not working
1. Check `.env` file has correct key
2. Check `BACKEND/config.py` has correct key
3. Rebuild containers: `docker-compose up --build`
4. Check backend logs: `docker-compose logs backend`

### Issue: Cannot connect to backend from frontend
1. Ensure `API_BASE_URL=http://backend:8000` in `.env`
2. Don't use `localhost` - use service name `backend`
3. Check both services are running: `docker-compose ps`

### Issue: Out of disk space
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything
docker system prune -a --volumes
```

### Issue: Build fails on dependencies
```bash
# Clear Docker cache
docker-compose build --no-cache

# Update requirements.txt
cd BACKEND && pip freeze > requirements.txt
cd ../FRONTEND && pip freeze > requirements.txt
```

---

## Development Workflow

### Code Changes

For development with hot-reload:

**Backend** (FastAPI auto-reloads):
```bash
# Already configured in Dockerfile CMD with --reload flag
docker-compose up
# Edit backend code → API reloads automatically
```

**Frontend** (Streamlit auto-reloads):
```bash
# Streamlit watches for file changes
docker-compose up
# Edit frontend code → UI reloads automatically
```

### Adding New Dependencies

1. Update `requirements.txt`:
   ```bash
   cd BACKEND  # or FRONTEND
   echo "new-package>=1.0.0" >> requirements.txt
   ```

2. Rebuild container:
   ```bash
   docker-compose build backend  # or frontend
   docker-compose up
   ```

### Debugging

Access container shell:
```bash
# Backend
docker-compose exec backend bash
python -c "import langchain; print(langchain.__version__)"

# Frontend
docker-compose exec frontend bash
streamlit --version
```

---

## Production Deployment

### Security Checklist
- [ ] Change default ports
- [ ] Use environment-specific `.env` files
- [ ] Never commit `.env` or `config.py`
- [ ] Use secrets management (Docker secrets, Kubernetes secrets)
- [ ] Enable HTTPS/TLS
- [ ] Set up authentication
- [ ] Configure firewall rules
- [ ] Enable rate limiting

### Recommended Changes for Production

**docker-compose.yml**:
```yaml
services:
  backend:
    restart: always  # Change from unless-stopped
    environment:
      - ENVIRONMENT=production
    # Add resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  frontend:
    restart: always
    # Use production Streamlit config
    command: streamlit run app.py --server.headless=true
```

### Using Docker Secrets (Docker Swarm)
```yaml
services:
  backend:
    secrets:
      - gemini_api_key
    environment:
      - GEMINI_API_KEY_FILE=/run/secrets/gemini_api_key

secrets:
  gemini_api_key:
    external: true
```

---

## Performance Optimization

### Build Time Optimization
```dockerfile
# Use multi-stage builds
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
```

### Runtime Optimization
- Use slim Python images (`python:3.11-slim`)
- Minimize layers in Dockerfile
- Use `.dockerignore` to exclude unnecessary files
- Pin dependency versions in `requirements.txt`

---

## Alternative: Docker without Compose

### Backend
```bash
# Build
docker build -t retail-insights-backend ./BACKEND

# Run
docker run -d \
  --name backend \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/BACKEND/config.py:/app/config.py \
  -e GEMINI_API_KEY=your-key \
  retail-insights-backend
```

### Frontend
```bash
# Build
docker build -t retail-insights-frontend ./FRONTEND

# Run
docker run -d \
  --name frontend \
  -p 8501:8501 \
  -e API_BASE_URL=http://backend:8000 \
  --link backend:backend \
  retail-insights-frontend
```

---

## Monitoring

### Health Checks
Both services have built-in health checks:

```bash
# Check health status
docker-compose ps

# View health check logs
docker inspect retail-insights-backend | grep -A 10 Health
```

### Resource Usage
```bash
# View resource usage
docker stats

# Limit resources in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

---

## FAQ

**Q: Can I run this on Windows?**
A: Yes! Docker Desktop works on Windows. Use PowerShell or WSL2.

**Q: Do I need to install Python?**
A: No! Docker containers include Python. You only need Docker installed.

**Q: How do I update the application?**
A: Pull latest code and rebuild: `git pull && docker-compose up --build`

**Q: Can I use a different LLM?**
A: Yes! Modify `BACKEND/utils.py` and `config.py` to use different LLM providers.

**Q: How do I backup my data?**
A: Copy the `./data` directory or use Docker volume backup tools.

---

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify API key is set correctly
3. Ensure ports 8000 and 8501 are available
4. Try rebuilding: `docker-compose up --build`
5. Check [GitHub Issues](your-repo-url/issues)

---

**Happy Dockerizing! 🐳**
