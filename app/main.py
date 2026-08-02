from typing import Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.services.rbac_service import get_allowed_departments, is_department_allowed
from app.services.document_loader import load_all_documents
from app.services.document_loader import load_all_documents, load_and_chunk_documents
from app.services.vector_store import build_vector_store, search_documents
from app.services.rag_service import answer_question
from app.services.monitoring_service import read_recent_logs

app = FastAPI()
security = HTTPBasic()

# Dummy user database
# Dummy user database
users_db: Dict[str, Dict[str, str]] = {
    "Tony": {"password": "password123", "role": "c_level"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "engineering"},
    "Sid": {"password": "sidpass123", "role": "employee"},
    "Natasha": {"password": "hrpass123", "role": "hr"}
}

# Authentication dependency
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)
    if not user or user.get("password") != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}


# Login endpoint
@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}


# Protected test endpoint
@app.get("/test")
def test(user=Depends(authenticate)):
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}


# Protected chat endpoint
@app.post("/chat")
def chat(message: str, user=Depends(authenticate)):
    result = answer_question(
        question=message,
        role=user["role"],
        username=user["username"]
    )

    return {
        "user": user["username"],
        "role": user["role"],
        "question": message,
        "allowed_departments": result["allowed_departments"],
        "answer": result["answer"],
        "sources": result["sources"],
        "retrieved_chunks_count": result["retrieved_chunks_count"],
        "guardrail_triggered": result["guardrail_triggered"],
        "guardrail_reason": result["guardrail_reason"],
        "model": result["model"],
        "estimated_input_tokens": result["estimated_input_tokens"],
        "estimated_output_tokens": result["estimated_output_tokens"],
        "estimated_total_tokens": result["estimated_total_tokens"]
    }

"""Test endpoint to verify document loading and RBAC functionality."""
@app.get("/documents/test")
def test_documents(user=Depends(authenticate)):
    documents = load_all_documents()

    return {
        "total_documents_loaded": len(documents),
        "sample_documents": [
            {
                "source": doc["source"],
                "department": doc["department"],
                "preview": doc["text"][:200]
            }
            for doc in documents[:5]
        ]
    }

""""""
@app.get("/chunks/test")
def test_chunks(user=Depends(authenticate)):
    chunks = load_and_chunk_documents()

    return {
        "total_chunks_created": len(chunks),
        "first_chunk": {
            "source": chunks[0]["source"],
            "department": chunks[0]["department"],
            "chunk_id": chunks[0]["chunk_id"],
            "preview": chunks[0]["text"][:300]
        } if chunks else None
    }

@app.post("/vector-store/build")
def build_store(user=Depends(authenticate)):
    result = build_vector_store()

    return {
        "user": user["username"],
        "role": user["role"],
        "result": result
    }


@app.get("/vector-store/search")
def search_store(question: str, user=Depends(authenticate)):
    allowed_departments = get_allowed_departments(user["role"])

    results = search_documents(
        question=question,
        allowed_departments=allowed_departments,
        top_k=5
    )

    return {
        "user": user["username"],
        "role": user["role"],
        "allowed_departments": allowed_departments,
        "question": question,
        "results": results
    }

@app.get("/monitoring/logs")
def get_logs(limit: int = 10, user=Depends(authenticate)):
    if user["role"] != "c_level":
        raise HTTPException(
            status_code=403,
            detail="Only C-level executives can access monitoring logs."
        )

    logs = read_recent_logs(limit=limit)

    return {
        "user": user["username"],
        "role": user["role"],
        "logs": logs
    }