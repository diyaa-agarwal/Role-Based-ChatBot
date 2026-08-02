# app/services/monitoring_service.py

import json
import re
from datetime import datetime
from pathlib import Path


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "chat_logs.jsonl"


def estimate_tokens(text: str):
    """
    Rough token estimate.
    Common simple approximation: 1 token ≈ 4 characters.
    """

    if not text:
        return 0

    return max(1, len(text) // 4)


def redact_text_for_logs(text: str):
    """
    Redacts sensitive values before storing logs.
    """

    if not text:
        return text

    # Redact emails
    text = re.sub(
        r"[\w\.-]+@[\w\.-]+\.\w+",
        "[REDACTED_EMAIL]",
        text
    )

    # Redact employee IDs
    text = re.sub(
        r"\bFINEMP\d+\b",
        "[REDACTED_EMPLOYEE_ID]",
        text
    )

    return text


def log_chat_event(event: dict):
    """
    Stores one chat event as JSONL.
    Each line is one request log.
    """

    LOG_DIR.mkdir(exist_ok=True)

    event["timestamp"] = datetime.utcnow().isoformat()

    if "question" in event:
        event["question"] = redact_text_for_logs(event["question"])

    if "answer" in event:
        event["answer"] = redact_text_for_logs(event["answer"])

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_recent_logs(limit: int = 10):
    """
    Reads recent chat logs for monitoring.
    """

    if not LOG_FILE.exists():
        return []

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()

    recent_lines = lines[-limit:]

    return [json.loads(line) for line in recent_lines]