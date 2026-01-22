"""
Text extraction from PDF, EPUB, DOCX, DOC, and TXT files.
"""

import re
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from docx import Document
from ebooklib import epub
from bs4 import BeautifulSoup


def extract_text(file_path: Path, file_type: str) -> str:
    """
    Route to appropriate extractor based on file type.
    Returns raw text content.
    """
    extractors = {
        "application/pdf": extract_pdf,
        "application/epub+zip": extract_epub,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_docx,
        "text/plain": extract_txt,
    }
    
    extractor = extractors.get(file_type)
    if not extractor:
        # Fallback: try to read as text
        return extract_txt(file_path)
    
    return extractor(file_path)


def extract_pdf(file_path: Path) -> str:
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(file_path)
    text_blocks = []
    
    for page in doc:
        text_blocks.append(page.get_text())
    
    doc.close()
    return "\n\n".join(text_blocks)


def extract_epub(file_path: Path) -> str:
    """Extract text from EPUB, preserving chapter order."""
    book = epub.read_epub(str(file_path))
    text_blocks = []
    
    for item in book.get_items_of_type(9):  # ITEM_DOCUMENT
        soup = BeautifulSoup(item.get_content(), "lxml")
        # Remove script and style elements
        for tag in soup(["script", "style"]):
            tag.decompose()
        text_blocks.append(soup.get_text(separator="\n"))
    
    return "\n\n".join(text_blocks)


def extract_docx(file_path: Path) -> str:
    """Extract text from DOCX, preserving paragraph structure."""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_txt(file_path: Path) -> str:
    """Read plain text file with encoding detection fallback."""
    encodings = ["utf-8", "latin-1", "cp1252"]
    
    for encoding in encodings:
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    
    # Last resort: read with error replacement
    return file_path.read_text(encoding="utf-8", errors="replace")


def clean_text(text: str) -> str:
    """
    Clean extracted text for TTS readability.
    - Remove excessive whitespace
    - Fix hyphenation from PDF line breaks
    - Normalize quotes and dashes
    """
    # Fix hyphenated line breaks (word- \nword -> word)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Normalize quotes
    text = text.replace(""", '"').replace(""", '"')
    text = text.replace("'", "'").replace("'", "'")
    
    # Normalize dashes
    text = text.replace("—", " - ").replace("–", " - ")
    
    return text.strip()


def chunk_into_paragraphs(text: str, min_length: int = 50) -> List[str]:
    """
    Split text into paragraph-sized chunks for TTS.
    Merges very short paragraphs with the next one.
    """
    # Split on double newlines (paragraph boundaries)
    raw_chunks = re.split(r"\n\s*\n", text)
    
    chunks = []
    buffer = ""
    
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        
        # Merge short chunks
        if len(buffer) + len(chunk) < min_length:
            buffer = f"{buffer} {chunk}".strip()
        else:
            if buffer:
                chunks.append(buffer)
            buffer = chunk
    
    # Don't forget the last buffer
    if buffer:
        chunks.append(buffer)
    
    return chunks
