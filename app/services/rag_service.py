# app/services/rag_service.py

from app.services.rbac_service import get_allowed_departments
from app.services.llm_service import generate_answer_from_context
from app.services.guardrail_service import (
    check_input_guardrails,
    sanitize_answer_for_role
)
from app.services.monitoring_service import log_chat_event
from app.services.vector_store import search_documents, search_documents_balanced, search_by_employee_ids
import re

def extract_employee_ids(question: str):
    matches = re.findall(r'\bFINEMP\d+\b', question, re.IGNORECASE)
    return [m.upper() for m in matches]

def prepare_sources(retrieved_docs: list):
    """
    Prepares unique source references from retrieved documents.
    """

    sources = []

    for doc in retrieved_docs:
        source_info = {
            "source": doc["source"],
            "department": doc["department"],
            "chunk_id": doc["chunk_id"]
        }

        if source_info not in sources:
            sources.append(source_info)

    return sources


def answer_question(question: str, role: str, username: str = "unknown"):
    """
    Main secure RAG function.

    Flow:
    1. Input guardrail
    2. RBAC
    3. Retrieval from allowed departments only
    4. LLM answer from authorized context only
    5. PII safety cleanup
    6. Logging and token tracking
    """

    allowed_departments = get_allowed_departments(role)

    guardrail_result = check_input_guardrails(question)

    if not guardrail_result["allowed"]:
        result = {
            "question": question,
            "allowed_departments": allowed_departments,
            "answer": guardrail_result["message"],
            "sources": [],
            "retrieved_chunks_count": 0,
            "guardrail_triggered": True,
            "guardrail_reason": guardrail_result["reason"],
            "model": None,
            "estimated_input_tokens": 0,
            "estimated_output_tokens": 0,
            "estimated_total_tokens": 0
        }

        log_chat_event({
            "username": username,
            "role": role,
            "question": question,
            "answer": result["answer"],
            "allowed_departments": allowed_departments,
            "sources": [],
            "retrieved_chunks_count": 0,
            "guardrail_triggered": True,
            "guardrail_reason": guardrail_result["reason"],
            "estimated_total_tokens": 0
        })

        return result
    employee_ids = extract_employee_ids(question)

    if employee_ids:
        # Employee ID lookup takes priority for ALL roles including c_level
        retrieved_docs = search_by_employee_ids(employee_ids, allowed_departments)
    
    elif role == "c_level" and len(allowed_departments) > 2:
        # Balanced retrieval only for broad c_level queries
        retrieved_docs = search_documents_balanced(
            question=question,
            allowed_departments=allowed_departments,
            top_k_per_dept=2
        )

    else:
        top_k = 10 if role in ["finance", "c_level"] else 5
        retrieved_docs = search_documents(
            question=question,
            allowed_departments=allowed_departments,
            top_k=top_k
        )

    llm_result = generate_answer_from_context(
        question=question,
        context_docs=retrieved_docs
    )

    safe_answer = sanitize_answer_for_role(
        answer=llm_result["answer"],
        role=role
    )

    if llm_result["answer_found"]:
        sources = prepare_sources(retrieved_docs)
    else:
        sources = []

    result = {
        "question": question,
        "allowed_departments": allowed_departments,
        "answer": safe_answer,
        "sources": sources,
        "retrieved_chunks_count": len(retrieved_docs),
        "guardrail_triggered": False,
        "guardrail_reason": None,
        "model": llm_result["model"],
        "estimated_input_tokens": llm_result["estimated_input_tokens"],
        "estimated_output_tokens": llm_result["estimated_output_tokens"],
        "estimated_total_tokens": llm_result["estimated_total_tokens"]
    }

    log_chat_event({
        "username": username,
        "role": role,
        "question": question,
        "answer": safe_answer,
        "allowed_departments": allowed_departments,
        "sources": sources,
        "retrieved_chunks_count": len(retrieved_docs),
        "guardrail_triggered": False,
        "guardrail_reason": None,
        "model": llm_result["model"],
        "estimated_input_tokens": llm_result["estimated_input_tokens"],
        "estimated_output_tokens": llm_result["estimated_output_tokens"],
        "estimated_total_tokens": llm_result["estimated_total_tokens"]
    })

    return result