# app/services/llm_service.py

import os
from google import genai

from app.services.monitoring_service import estimate_tokens


MODEL_NAME = "gemini-2.5-flash"


def build_context_text(context_docs: list):
    """
    Converts retrieved chunks into clean context for the LLM.
    """

    context_parts = []

    for index, doc in enumerate(context_docs, start=1):
        context_parts.append(
            f"""
[Source {index}]
Department: {doc["department"]}
Source file: {doc["source"]}
Chunk ID: {doc["chunk_id"]}

Content:
{doc["text"]}
"""
        )

    return "\n\n".join(context_parts)


def generate_answer_from_context(question: str, context_docs: list):
    """
    Uses Gemini to generate an answer from authorized context only.
    Also returns approximate token usage.
    """

    if not context_docs:
        return {
            "answer": "I could not find relevant information in the documents available to your role.",
            "answer_found": False,
            "model": MODEL_NAME,
            "estimated_input_tokens": 0,
            "estimated_output_tokens": 0,
            "estimated_total_tokens": 0
        }

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "answer": "LLM is not configured. Please set GEMINI_API_KEY before running the server.",
            "answer_found": False,
            "model": MODEL_NAME,
            "estimated_input_tokens": 0,
            "estimated_output_tokens": 0,
            "estimated_total_tokens": 0
        }

    context_text = build_context_text(context_docs)

    prompt = f"""
You are a secure internal company chatbot for FinSolve Technologies.

Rules:
1. Answer ONLY using the authorized context given below.
2. Do NOT use outside knowledge.
3. Do NOT guess.
4. If the context does not contain the answer, reply exactly:
INSUFFICIENT_INFORMATION: I could not find this information in the documents available to your role.
5. Keep the answer clear and concise.
6. Do not write source file names or chunk IDs inside the answer. The backend will return sources separately.
7. If the user asks something unrelated to FinSolve company documents, reply exactly:
INSUFFICIENT_INFORMATION: I could not find this information in the documents available to your role.
8. If the question is ambiguous or very short, clarify what the answer covers (e.g., quarterly vs annual, which year) before giving the data.
9. If you find partial data (e.g., only some quarters of a year), state clearly that the answer is based on available context and may be incomplete.
10. If a question asks to compare or cross-reference data from multiple departments but context only covers some departments, explicitly state which departments' data is included in the answer.
11. If both a summary figure and a detailed breakdown exist in context, present the detailed breakdown and mention the summary figure is the annual average.
User question:
12. If the question requires a calculation (e.g. revenue per employee, ratio, percentage), and all the required data points are present in context, perform the calculation and show your working clearly.
{question}

Authorized context:
{context_text}
"""

    estimated_input_tokens = estimate_tokens(prompt)

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        answer = response.text.strip()
        estimated_output_tokens = estimate_tokens(answer)

        if answer.startswith("INSUFFICIENT_INFORMATION"):
            return {
                "answer": "I could not find this information in the documents available to your role.",
                "answer_found": False,
                "model": MODEL_NAME,
                "estimated_input_tokens": estimated_input_tokens,
                "estimated_output_tokens": estimated_output_tokens,
                "estimated_total_tokens": estimated_input_tokens + estimated_output_tokens
            }

        return {
            "answer": answer,
            "answer_found": True,
            "model": MODEL_NAME,
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_total_tokens": estimated_input_tokens + estimated_output_tokens
        }

    except Exception as e:
        return {
            "answer": f"LLM error: {str(e)}",
            "answer_found": False,
            "model": MODEL_NAME,
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": 0,
            "estimated_total_tokens": estimated_input_tokens
        }