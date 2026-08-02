# app/services/vector_store.py

import chromadb

from app.services.document_loader import load_and_chunk_documents


CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "finsolve_documents"


def get_chroma_client():
    """
    Creates a persistent ChromaDB client.
    Data will be stored inside the chroma_db folder.
    """
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_or_create_collection():
    """
    Gets the existing collection or creates a new one.
    """
    client = get_chroma_client()

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    return collection


def reset_collection():
    """
    Deletes the old collection if it exists.
    This prevents duplicate chunks when rebuilding the vector store.
    """
    client = get_chroma_client()

    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    return collection


def build_vector_store():
    """
    Loads chunked documents and stores them in ChromaDB.
    """

    collection = reset_collection()

    chunks = load_and_chunk_documents()

    ids = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(f"chunk_{index}")

        documents.append(chunk["text"])

        metadatas.append({
            "source": chunk["source"],
            "department": chunk["department"],
            "chunk_id": chunk["chunk_id"],
            "employee_id": chunk.get("employee_id", "")
        })

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    return {
        "message": "Vector store built successfully",
        "total_chunks_added": len(chunks)
    }


def search_documents(question: str, allowed_departments: list, top_k: int = 5):
    """
    Searches ChromaDB for relevant chunks.
    It only searches inside departments allowed for the user's role.
    """

    collection = get_or_create_collection()

    results = collection.query(
        query_texts=[question],
        n_results=top_k,
        where={
            "department": {
                "$in": allowed_departments
            }
        }
    )

    retrieved_docs = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc_text, metadata, distance in zip(documents, metadatas, distances):
        retrieved_docs.append({
            "text": doc_text,
            "source": metadata["source"],
            "department": metadata["department"],
            "chunk_id": metadata["chunk_id"],
            "distance": distance
        })

    return retrieved_docs

def search_by_employee_ids(employee_ids: list, allowed_departments: list):
    collection = get_or_create_collection()
    all_docs = []
    seen_ids = set()

    for emp_id in employee_ids:
        results = collection.query(
            query_texts=[emp_id],
            n_results=3,  # small — we want exact rows only
            where={
                "$and": [
                    {"department": {"$in": allowed_departments}},
                    {"employee_id": {"$eq": emp_id}}
                ]
            }
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_text, metadata, distance in zip(documents, metadatas, distances):
            uid = metadata.get("employee_id", "") + str(metadata.get("chunk_id", ""))
            if uid not in seen_ids:
                seen_ids.add(uid)
                all_docs.append({
                    "text": doc_text,
                    "source": metadata["source"],
                    "department": metadata["department"],
                    "chunk_id": metadata["chunk_id"],
                    "distance": distance
                })

    return all_docs

def search_documents_balanced(question: str, allowed_departments: list, top_k_per_dept: int = 2):
    """
    Fetches top_k chunks per department separately to avoid one department dominating.
    """
    collection = get_or_create_collection()
    all_docs = []

    for dept in allowed_departments:
        results = collection.query(
            query_texts=[question],
            n_results=top_k_per_dept,
            where={"department": {"$eq": dept}}
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_text, metadata, distance in zip(documents, metadatas, distances):
            all_docs.append({
                "text": doc_text,
                "source": metadata["source"],
                "department": metadata["department"],
                "chunk_id": metadata["chunk_id"],
                "distance": distance
            })

    # Sort by relevance across all departments
    all_docs.sort(key=lambda x: x["distance"])
    return all_docs