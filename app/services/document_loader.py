# app/services/document_loader.py

from pathlib import Path
import csv
from app.utils.text_splitter import split_text_into_chunks


DATA_DIR = Path("resources/data")


def load_markdown_file(file_path: Path):
    """
    Reads a .md file and returns its text.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def load_csv_file(file_path: Path):
    """
    Reads a .csv file and converts each row into readable text.
    This is useful for HR data.
    """
    documents = []

    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=1):
            row_text = "\n".join(
                [f"{key}: {value}" for key, value in row.items()]
            )

            documents.append({
                "text": row_text,
                "source": str(file_path),
                "department": file_path.parent.name,
                "row_number": row_number,
                "employee_id": row.get("employee_id", "")   
            })

    return documents


def load_all_documents():
    """
    Loads all documents from resources/data folder.
    Returns a list of documents with text and metadata.
    """
    all_documents = []

    for department_folder in DATA_DIR.iterdir():
        if not department_folder.is_dir():
            continue

        department = department_folder.name

        for file_path in department_folder.iterdir():
            if file_path.suffix == ".md":
                text = load_markdown_file(file_path)

                all_documents.append({
                    "text": text,
                    "source": str(file_path),
                    "department": department
                })

            elif file_path.suffix == ".csv":
                csv_documents = load_csv_file(file_path)
                all_documents.extend(csv_documents)

    return all_documents

def load_and_chunk_documents():
    """
    Loads all documents and splits them into smaller chunks.
    Returns chunked documents with metadata.
    """

    documents = load_all_documents()
    chunked_documents = []

    for doc in documents:
        if doc["source"].endswith(".csv"):
            chunked_documents.append({
                "text": doc["text"],
                "source": doc["source"],
                "department": doc["department"],
                "chunk_id": 0,
                "employee_id": doc.get("employee_id", "")
            })
        else:
            chunks = split_text_into_chunks(doc["text"])
            for chunk_index, chunk_text in enumerate(chunks):
                chunked_documents.append({
                    "text": chunk_text,
                    "source": doc["source"],
                    "department": doc["department"],
                    "chunk_id": chunk_index,
                    "employee_id": doc.get("employee_id", "")
                })

    return chunked_documents