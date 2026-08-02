# app/services/guardrail_service.py

import re


PROMPT_INJECTION_PATTERNS = [
    # existing ones...
    "reveal the hidden",
    "reveal system rules",
    "reveal hidden rules",
    "for debugging purposes",
    "retrieve.*payroll",
    "retrieve.*salary",
    "show.*system rules",
    "show.*hidden",
    "show all.*data",
    "print.*database",
    "dump.*data",
    "list all employees",
    "show me all",
    "pretend you are",
    "you are now",
    "jailbreak",
    "developer mode",
    "do anything now",
    "dan mode",
]

INJECTION_REGEX_PATTERNS = [
    r"(reveal|show|print|dump|expose)\s+(hidden|secret|system|all|internal)",
    r"for\s+(debugging|testing|demo)\s+(purposes|mode)",
    r"(retrieve|fetch|get|access)\s+(payroll|salary|hr|confidential)\s+(data|info)",
]

def check_input_guardrails(question: str):
    """
    Checks whether the user query is trying to bypass security rules.
    This is not department detection.
    This only blocks unsafe prompt-injection style requests.
    """

    question_lower = question.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern in question_lower:
            return {
                "allowed": False,
                "reason": "Prompt injection attempt detected.",
                "message": "I cannot process requests that try to bypass security, RBAC, or system instructions."
            }

    for pattern in INJECTION_REGEX_PATTERNS:
        if re.search(pattern, question_lower):
            return {
                "allowed": False,
                "reason": "Prompt injection attempt detected.",
                "message": "I cannot process requests that try to bypass security, RBAC, or system instructions."
            }

    if len(question.strip()) < 3:
        return {
            "allowed": False,
            "reason": "Question too short.",
            "message": "Please ask a more specific company-related question."
        }

    return {
        "allowed": True,
        "reason": None,
        "message": None
    }


def sanitize_answer_for_role(answer: str, role: str):
    """
    Redacts sensitive employee-level PII from the answer for non-HR and non-C-level roles.
    RBAC already prevents unauthorized retrieval.
    This is an additional safety layer.
    """

    if role in ["hr", "c_level"]:
        return answer

    # Mask email addresses
    answer = re.sub(
        r"[\w\.-]+@[\w\.-]+\.\w+",
        "[REDACTED_EMAIL]",
        answer
    )

    # Mask employee IDs
    answer = re.sub(
        r"\bFINEMP\d+\b",
        "[REDACTED_EMPLOYEE_ID]",
        answer
    )

    # Mask date of birth patterns
    answer = re.sub(
        r"(date of birth|dob)\s*[:\-]?\s*\d{4}-\d{2}-\d{2}",
        r"\1: [REDACTED_DOB]",
        answer,
        flags=re.IGNORECASE
    )

    # Mask direct salary field patterns, but not general salary policy text
    answer = re.sub(
        r"(salary)\s*[:\-]\s*[\₹\$]?\d[\d,\.]+",
        r"\1: [REDACTED]",
        answer,
        flags=re.IGNORECASE
    )

    return answer