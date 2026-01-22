# Auto-Reader

File-to-speech with position persistence. Upload a document, press play, pause whenever, close the browser, come back later—it picks up where you left off.

## The Problem

OS text-to-speech (highlight text → right-click → "Speak") loses your position when you stop. Long documents become unmanageable.

## The Solution

Web Speech API in browser with localStorage tracking paragraph and word position.

## Features

- **Supported formats**: PDF, EPUB, DOCX, TXT, Markdown
- **Controls**: Play, Pause, Stop, Previous/Next chunk, Reset
- **Position tracking**: Saves paragraph + word index to localStorage
- **Persistence**: Survives browser refresh, keyed by filename
- **Speed control**: 0.5x to 2x
- **Voice selection**: Uses available system voices

## Setup

```bash
cd auto-reader
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`

## Architecture

```
Upload → Extract text (PyMuPDF/ebooklib/python-docx)
              ↓
         Clean text (fix hyphenation, normalize whitespace)
              ↓
         Chunk into paragraphs
              ↓
         Web Speech API (browser JS)
              ↓
         onboundary event → update word index
              ↓
         localStorage → persist position
```

## Limitations

- Voice quality depends on OS/browser
- Tab must stay visible (browser restricts background audio)
- DOC format (legacy Word) not supported—convert to DOCX first

## File Structure

```
auto-reader/
├── app.py           # Streamlit app + JS component
├── extractors.py    # Text extraction by format
├── requirements.txt
└── README.md
```
