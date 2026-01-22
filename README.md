# Auto-Reader

v1.0.1

Upload a document. Press play. Pause. Close browser. Return. Resume from exact position.

## Problem

OS text-to-speech loses position on stop. Long documents become unnavigable.

## Solution

Pre-generate audio via edge-tts (Microsoft neural voices). Track chunk + timestamp in localStorage.

## Features

- **Formats**: PDF, EPUB, DOCX, TXT, Markdown
- **Controls**: Play, Pause, Stop, Previous/Next chunk, Reset
- **Persistence**: Chunk index + playback time saved per document
- **Speed**: 0.5x to 2x
- **Voice**: en-US-JennyNeural (female, US English)

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
         Clean text (dehyphenate, normalize)
              ↓
         Chunk into paragraphs
              ↓
         Generate audio per chunk (edge-tts)
              ↓
         HTML5 audio player
              ↓
         localStorage persistence
```

## Limitations

- Requires internet (edge-tts uses Microsoft servers)
- Initial audio generation takes time proportional to document length
- DOC format unsupported (convert to DOCX)

## Files

```
auto-reader/
├── app.py           # Streamlit app + audio player
├── extractors.py    # Text extraction
├── requirements.txt
└── README.md
```
