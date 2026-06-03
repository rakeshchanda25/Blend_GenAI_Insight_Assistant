import json
import re
import logging
import google.genai as genai
from config import GEMINI_API_KEY, LLM_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiClient:
    """Wrapper for Gemini API calls."""

    def __init__(self):
        self.model = LLM_CONFIG["model"]
        self.temperature = LLM_CONFIG["temperature"]
        self.max_tokens = LLM_CONFIG["max_tokens"]
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def generate(self, prompt: str) -> str:
        """This function help to generate response from LLM"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def generate_json(self, prompt: str) -> dict:
        """This function help to generate response from LLM in json format"""
        response = self.generate(prompt)
        return parse_json_response(response)


def parse_json_response(text: str) -> dict:
    """This function help to parse the json response"""
    ### Try Normal JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    ### parse JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object pattern
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to parse JSON from: {text[:200]}")
    return {}


def dataframe_to_text(df, max_rows: int = 10) -> str:
    """Convert DataFrame to readable text."""
    if df is None or df.empty:
        return "No data available"

    preview = df.head(max_rows)
    lines = [" | ".join(str(v) for v in row) for _, row in preview.iterrows()]
    header = " | ".join(df.columns)

    result = f"Columns: {header}\n"
    result += "\n".join(lines)

    if len(df) > max_rows:
        result += f"\n... and {len(df) - max_rows} more rows"

    return result


# ============== SQL INJECTION DETECTION ==============

from typing import Tuple, List

# SQL Injection Detection Patterns (blacklist approach)
SQL_INJECTION_PATTERNS = [
    # Destructive operations
    (r'\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE)\b', 'Destructive SQL operation detected'),

    # Multiple statements (chained queries)
    (r';\s*(SELECT|DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|TRUNCATE)', 'Multiple SQL statements detected'),

    # UNION-based injection
    (r'\bUNION\s+(ALL\s+)?SELECT\b', 'UNION injection pattern detected'),

    # Comment-based injection
    (r'(--|/\*|\*/|#)', 'SQL comment injection pattern detected'),

    # System table access
    (r'\b(sqlite_master|information_schema|sys\.|sysobjects)\b', 'System table access detected'),

    # Dangerous functions
    (r'\b(SLEEP|BENCHMARK|LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b', 'Dangerous SQL function detected'),

    # Hex/char encoding (common obfuscation)
    (r'(0x[0-9a-fA-F]+|CHAR\s*\()', 'Encoded/obfuscated SQL detected'),

    # Tautologies (always-true conditions often used in injection)
    (r"('\s*OR\s*'?\d+'\s*=\s*'?\d+|1\s*=\s*1|'a'\s*=\s*'a')", 'SQL injection tautology detected'),
]


def detect_sql_injection(sql: str) -> Tuple[bool, List[str]]:
    """
    Detect potential SQL injection patterns in a query.

    Args:
        sql: The SQL query string to analyze

    Returns:
        Tuple of (is_safe, list_of_issues)
    """
    if not sql:
        return True, []

    issues = []
    sql_upper = sql.upper()

    for pattern, message in SQL_INJECTION_PATTERNS:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            issues.append(message)

    is_safe = len(issues) == 0
    return is_safe, issues


def validate_sql_whitelist(sql: str) -> Tuple[bool, List[str]]:
    """
    Whitelist approach: only allow SELECT statements on allowed tables.

    Args:
        sql: The SQL query string to analyze

    Returns:
        Tuple of (is_allowed, list_of_issues)
    """
    if not sql:
        return True, []

    sql_stripped = sql.strip().upper()
    issues = []

    # Only allow SELECT statements
    if not sql_stripped.startswith('SELECT'):
        issues.append('Only SELECT statements are allowed')
        return False, issues

    # Check for allowed tables (whitelist approach)
    allowed_tables = ['SALES_DATA']

    # Extract table name from FROM clause
    from_match = re.search(r'\bFROM\s+(\w+)', sql_stripped)
    if from_match:
        table_name = from_match.group(1)
        if table_name not in allowed_tables:
            issues.append(f'Table "{table_name}" is not in allowed list')

    return len(issues) == 0, issues
