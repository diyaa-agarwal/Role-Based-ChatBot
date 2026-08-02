# app/utils/text_splitter.py

def split_text_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    """
    Splits text into smaller chunks safely.
    """

    if not text:
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # Important: stop when we reach the end
        if end == text_length:
            break

        start = end - chunk_overlap

    return chunks