"""
Frontend Configuration Example
Copy this file to config.py and customize as needed
"""

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Backend API URL
API_TIMEOUT = 600  # Request timeout in seconds

# UI Configuration
PAGE_TITLE = "Retail Insights Assistant"
PAGE_ICON = "📊"
LAYOUT = "wide"  # "centered" or "wide"

# Feature Flags
ENABLE_UPLOAD = True
ENABLE_QA = True
ENABLE_SUMMARY = True
ENABLE_HISTORY = True

# Display Settings
MAX_HISTORY_ITEMS = 5  # Number of Q&A pairs to show in history
SHOW_DEBUG_INFO = False  # Show debug information

# Styling
PRIMARY_COLOR = "#1f77b4"
BACKGROUND_COLOR = "#ffffff"
SECONDARY_BG_COLOR = "#f0f2f6"

# File Upload Settings
ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls", "json", "txt"]
MAX_FILE_SIZE_MB = 100  # Maximum file size in MB

# Example Questions
EXAMPLE_QUESTIONS = [
    "What are the top 5 products by sales?",
    "Show me total revenue by region",
    "Which category has the highest average price?",
    "What insights do we have about customer behavior?",
    "Summarize the sales trends"
]
