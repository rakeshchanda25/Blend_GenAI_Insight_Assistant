"""
Data Ingestion Script for ChromaDB
Ingests JSON/TXT files into ChromaDB for semantic search and RAG.

Usage:
    python ingest_data_to_chromadb.py <file_path>

Example:
    python ingest_data_to_chromadb.py data/insights.json
    python ingest_data_to_chromadb.py data/summary.txt
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import logging
import chromadb
from chromadb.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ChromaDB configuration
CHROMA_PATH = "data/chroma"
COLLECTION_NAME = "sales_insights"


def get_chromadb_client():
    """Create and return ChromaDB client."""
    chroma_dir = Path(CHROMA_PATH)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False)
    )
    return client


def get_or_create_collection(client):
    """Get or create ChromaDB collection."""
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        logger.info(f"Using existing collection: {COLLECTION_NAME}")
    except:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Retail sales insights and summaries"}
        )
        logger.info(f"Created new collection: {COLLECTION_NAME}")

    return collection


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Overlapping characters between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)

            if break_point > chunk_size // 2:  # Only break if not too early
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return chunks


def read_file_content(file_path: str) -> Dict[str, Any]:
    """
    Read file content based on extension.

    Args:
        file_path: Path to file

    Returns:
        dict with content and metadata
    """
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = file_path_obj.suffix.lower()

    if file_ext == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle different JSON structures
        if isinstance(data, dict):
            # If it's a dict, convert to readable text
            content = json.dumps(data, indent=2)
            metadata = {
                "source": file_path_obj.name,
                "type": "json_object",
                "keys": list(data.keys()) if isinstance(data, dict) else []
            }
        elif isinstance(data, list):
            # If it's a list, join items
            content = "\n\n".join([json.dumps(item, indent=2) for item in data])
            metadata = {
                "source": file_path_obj.name,
                "type": "json_array",
                "items": len(data)
            }
        else:
            content = str(data)
            metadata = {
                "source": file_path_obj.name,
                "type": "json_value"
            }

    elif file_ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        metadata = {
            "source": file_path_obj.name,
            "type": "text"
        }

    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Use JSON or TXT.")

    return {
        "content": content,
        "metadata": metadata
    }


def ingest_to_chromadb(file_path: str) -> dict:
    """
    Ingest JSON or TXT file into ChromaDB.

    Args:
        file_path: Path to JSON or TXT file

    Returns:
        dict with status information
    """
    try:
        logger.info(f"Reading file: {file_path}")

        # Read file content
        file_data = read_file_content(file_path)
        content = file_data["content"]
        base_metadata = file_data["metadata"]

        logger.info(f"Content length: {len(content)} characters")

        # Chunk the content
        chunks = chunk_text(content, chunk_size=1000, overlap=200)
        logger.info(f"Created {len(chunks)} chunks")

        # Get ChromaDB client and collection
        client = get_chromadb_client()
        collection = get_or_create_collection(client)

        # Prepare data for insertion
        documents = chunks
        ids = [f"{base_metadata['source']}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                **base_metadata,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]

        # Insert into ChromaDB
        logger.info(f"Inserting {len(documents)} chunks into ChromaDB...")
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

        # Verify insertion
        total_count = collection.count()

        result = {
            "success": True,
            "message": f"Successfully ingested {len(chunks)} chunks into ChromaDB",
            "chunks": len(chunks),
            "total_documents": total_count,
            "collection_name": COLLECTION_NAME,
            "chroma_path": CHROMA_PATH,
            "source_file": Path(file_path).name
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


def get_collection_info() -> dict:
    """Get information about the ChromaDB collection."""
    try:
        client = get_chromadb_client()
        collection = client.get_collection(name=COLLECTION_NAME)

        total_count = collection.count()

        # Get sample documents
        sample = collection.peek(limit=3)

        return {
            "collection_name": COLLECTION_NAME,
            "total_documents": total_count,
            "sample_documents": [
                {
                    "id": sample["ids"][i],
                    "content_preview": sample["documents"][i][:200] + "...",
                    "metadata": sample["metadatas"][i]
                }
                for i in range(min(3, len(sample["ids"])))
            ]
        }

    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        return None


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python ingest_data_to_chromadb.py <file_path>")
        print("\nExample:")
        print("  python ingest_data_to_chromadb.py data/insights.json")
        print("  python ingest_data_to_chromadb.py data/summary.txt")
        sys.exit(1)

    file_path = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"ChromaDB Data Ingestion")
    print(f"{'='*60}")
    print(f"File: {file_path}")
    print(f"ChromaDB Path: {CHROMA_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"{'='*60}\n")

    # Ingest data
    result = ingest_to_chromadb(file_path)

    if result["success"]:
        print(f"\n✅ SUCCESS!")
        print(f"   Chunks ingested: {result['chunks']}")
        print(f"   Total documents in collection: {result['total_documents']}")
        print(f"   ChromaDB path: {result['chroma_path']}")

        # Show collection info
        print(f"\n{'='*60}")
        print("Collection Information:")
        print(f"{'='*60}")
        info = get_collection_info()
        if info:
            print(f"Total documents: {info['total_documents']}")

            print(f"\nSample documents:")
            for i, doc in enumerate(info['sample_documents'], 1):
                print(f"\n  Document {i}:")
                print(f"    ID: {doc['id']}")
                print(f"    Source: {doc['metadata'].get('source', 'N/A')}")
                print(f"    Type: {doc['metadata'].get('type', 'N/A')}")
                print(f"    Content preview: {doc['content_preview']}")
    else:
        print(f"\n❌ FAILED!")
        print(f"   Error: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
