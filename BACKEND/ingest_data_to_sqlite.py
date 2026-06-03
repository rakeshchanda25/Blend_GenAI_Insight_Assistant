"""
Data Ingestion Script for SQLite
Ingests CSV/Excel files into SQLite database for structured data queries.

Usage:
    python ingest_data_to_sqlite.py <file_path>

Example:
    python ingest_data_to_sqlite.py data/sales.csv
    python ingest_data_to_sqlite.py data/sales.xlsx
"""

import sys
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = "data/sales.db"
TABLE_NAME = "sales_data"


def get_sqlite_connection() -> sqlite3.Connection:
    """Create and return SQLite connection."""
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ingest_csv_to_sqlite(file_path: str, table_name: str = TABLE_NAME) -> dict:
    """
    Ingest CSV or Excel file into SQLite database.

    Args:
        file_path: Path to CSV or Excel file
        table_name: Name of table to create/append to

    Returns:
        dict with status information
    """
    try:
        file_path_obj = Path(file_path)

        # Validate file exists
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file based on extension
        file_ext = file_path_obj.suffix.lower()

        logger.info(f"Reading file: {file_path}")
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Use CSV or Excel.")

        if df.empty:
            raise ValueError("File is empty")

        logger.info(f"Loaded {len(df)} rows with {len(df.columns)} columns")
        logger.info(f"Columns: {list(df.columns)}")

        # Connect to database
        conn = get_sqlite_connection()

        # Insert data (replace existing table)
        logger.info(f"Inserting data into table '{table_name}'...")
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        # Verify insertion
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]

        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]

        conn.close()

        result = {
            "success": True,
            "message": f"Successfully ingested {row_count} rows into '{table_name}'",
            "rows": row_count,
            "columns": columns,
            "table_name": table_name,
            "database": DB_PATH
        }

        logger.info(f"✅ {result['message']}")
        return result

    except Exception as e:
        logger.error(f"❌ Error ingesting data: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "error": str(e)
        }


def get_table_info(table_name: str = TABLE_NAME) -> Optional[dict]:
    """Get information about the table."""
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if not cursor.fetchone():
            return None

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]

        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [
            {"name": row[1], "type": row[2]}
            for row in cursor.fetchall()
        ]

        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        sample_rows = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "table_name": table_name,
            "row_count": row_count,
            "columns": columns,
            "sample_data": sample_rows
        }

    except Exception as e:
        logger.error(f"Error getting table info: {e}")
        return None


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python ingest_data_to_sqlite.py <file_path>")
        print("\nExample:")
        print("  python ingest_data_to_sqlite.py data/sales.csv")
        print("  python ingest_data_to_sqlite.py data/sales.xlsx")
        sys.exit(1)

    file_path = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"SQLite Data Ingestion")
    print(f"{'='*60}")
    print(f"File: {file_path}")
    print(f"Database: {DB_PATH}")
    print(f"Table: {TABLE_NAME}")
    print(f"{'='*60}\n")

    # Ingest data
    result = ingest_csv_to_sqlite(file_path)

    if result["success"]:
        print(f"\n✅ SUCCESS!")
        print(f"   Rows inserted: {result['rows']}")
        print(f"   Columns: {', '.join(result['columns'])}")
        print(f"   Database: {result['database']}")

        # Show table info
        print(f"\n{'='*60}")
        print("Table Information:")
        print(f"{'='*60}")
        info = get_table_info()
        if info:
            print(f"Total rows: {info['row_count']}")
            print(f"\nColumns:")
            for col in info['columns']:
                print(f"  - {col['name']} ({col['type']})")

            print(f"\nSample data (first 5 rows):")
            for i, row in enumerate(info['sample_data'], 1):
                print(f"\n  Row {i}:")
                for key, value in row.items():
                    print(f"    {key}: {value}")
    else:
        print(f"\n❌ FAILED!")
        print(f"   Error: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
