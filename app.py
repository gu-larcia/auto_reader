"""
Auto-Reader: File-to-speech with position persistence.
Uses browser's Web Speech API for TTS with pause/resume capability.
"""

import json
import tempfile
from pathlib import Path

import streamlit as st
from streamlit.components.v1 import html

from extractors import extract_text, clean_text, chunk_into_paragraphs


# Page config
st.set_page_config(
    page_title="Auto-Reader",
    page_icon="📖",
    layout="centered",
)

# Minimal CSS
st.markdown("""
<style>
    .stApp {
        max-width: 800px;
        margin: 0 auto;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def get_tts_component(chunks: list[str], doc_id: str) -> str:
    """
    Generate HTML/JS component for Web Speech API TTS.
    
    Features:
    - Play/Pause/Stop controls
    - Speed slider
    - Voice selector
    - Position tracking (paragraph + word index)
    - localStorage persistence keyed by doc_id
    """
    chunks_json = json.dumps(chunks)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                box-sizing: border-box;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            body {{
                margin: 0;
                padding: 16px;
                background: #0e1117;
                color: #fafafa;
            }}
            .controls {{
                display: flex;
                gap: 8px;
                margin-bottom: 16px;
                flex-wrap: wrap;
                align-items: center;
            }}
            button {{
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.15s ease;
            }}
            button:disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
            .play-btn {{
                background: #4CAF50;
                color: white;
            }}
            .play-btn:hover:not(:disabled) {{
                background: #45a049;
            }}
            .pause-btn {{
                background: #ff9800;
                color: white;
            }}
            .pause-btn:hover:not(:disabled) {{
                background: #f57c00;
            }}
            .stop-btn {{
                background: #f44336;
                color: white;
            }}
            .stop-btn:hover:not(:disabled) {{
                background: #d32f2f;
            }}
            .settings {{
                display: flex;
                gap: 16px;
                margin-bottom: 16px;
                flex-wrap: wrap;
                align-items: center;
            }}
            .setting {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            label {{
                font-size: 13px;
                color: #aaa;
            }}
            select, input[type="range"] {{
                background: #262730;
                border: 1px solid #444;
                border-radius: 4px;
                color: #fafafa;
                padding: 6px 10px;
            }}
            input[type="range"] {{
                width: 100px;
            }}
            .progress {{
                font-size: 13px;
                color: #888;
                margin-bottom: 12px;
            }}
            .chunk-display {{
                background: #1a1d24;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
                font-size: 18px;
                line-height: 1.7;
                min-height: 120px;
                white-space: pre-wrap;
            }}
            .word {{
                transition: background 0.1s;
            }}
            .word.current {{
                background: #4CAF50;
                color: white;
                padding: 2px 4px;
                border-radius: 3px;
            }}
            .nav-buttons {{
                display: flex;
                gap: 8px;
                margin-top: 12px;
            }}
            .nav-btn {{
                background: #262730;
                color: #fafafa;
                padding: 8px 16px;
                font-size: 13px;
            }}
            .nav-btn:hover:not(:disabled) {{
                background: #363740;
            }}
        </style>
    </head>
    <body>
        <div class="controls">
            <button class="play-btn" id="playBtn" onclick="play()">▶ Play</button>
            <button class="pause-btn" id="pauseBtn" onclick="pause()" disabled>⏸ Pause</button>
            <button class="stop-btn" id="stopBtn" onclick="stop()" disabled>⏹ Stop</button>
        </div>
        
        <div class="settings">
            <div class="setting">
                <label for="voice">Voice:</label>
                <select id="voice"></select>
            </div>
            <div class="setting">
                <label for="rate">Speed:</label>
                <input type="range" id="rate" min="0.5" max="2" step="0.1" value="1">
                <span id="rateVal">1.0x</span>
            </div>
        </div>
        
        <div class="progress" id="progress">Ready</div>
        
        <div class="chunk-display" id="chunkDisplay">
            Upload a file and press Play to begin.
        </div>
        
        <div class="nav-buttons">
            <button class="nav-btn" onclick="prevChunk()">← Previous</button>
            <button class="nav-btn" onclick="nextChunk()">Next →</button>
            <button class="nav-btn" onclick="resetPosition()">↺ Reset</button>
        </div>
        
        <script>
            const DOC_ID = "{doc_id}";
            const STORAGE_KEY = "autoreader_" + DOC_ID;
            const chunks = {chunks_json};
            
            let synth = window.speechSynthesis;
            let utterance = null;
            let currentChunk = 0;
            let currentWord = 0;
            let isPaused = false;
            let voices = [];
            let selectedVoice = null;
            
            // Load voices
            function loadVoices() {{
                voices = synth.getVoices();
                const select = document.getElementById("voice");
                select.innerHTML = "";
                
                voices.forEach((voice, i) => {{
                    const option = document.createElement("option");
                    option.value = i;
                    option.textContent = voice.name + " (" + voice.lang + ")";
                    if (voice.default) option.selected = true;
                    select.appendChild(option);
                }});
                
                // Load saved voice preference
                const saved = localStorage.getItem(STORAGE_KEY + "_voice");
                if (saved && voices[saved]) {{
                    select.value = saved;
                }}
                selectedVoice = voices[select.value];
            }}
            
            if (synth.onvoiceschanged !== undefined) {{
                synth.onvoiceschanged = loadVoices;
            }}
            loadVoices();
            
            document.getElementById("voice").onchange = function() {{
                selectedVoice = voices[this.value];
                localStorage.setItem(STORAGE_KEY + "_voice", this.value);
            }};
            
            // Rate slider
            const rateSlider = document.getElementById("rate");
            const rateVal = document.getElementById("rateVal");
            rateSlider.oninput = function() {{
                rateVal.textContent = parseFloat(this.value).toFixed(1) + "x";
                localStorage.setItem(STORAGE_KEY + "_rate", this.value);
            }};
            
            // Load saved rate
            const savedRate = localStorage.getItem(STORAGE_KEY + "_rate");
            if (savedRate) {{
                rateSlider.value = savedRate;
                rateVal.textContent = parseFloat(savedRate).toFixed(1) + "x";
            }}
            
            // Load saved position
            function loadPosition() {{
                const saved = localStorage.getItem(STORAGE_KEY);
                if (saved) {{
                    const pos = JSON.parse(saved);
                    currentChunk = Math.min(pos.chunk || 0, chunks.length - 1);
                    currentWord = pos.word || 0;
                }}
                updateDisplay();
            }}
            
            function savePosition() {{
                localStorage.setItem(STORAGE_KEY, JSON.stringify({{
                    chunk: currentChunk,
                    word: currentWord
                }}));
            }}
            
            function updateProgress() {{
                const pct = Math.round(((currentChunk + 1) / chunks.length) * 100);
                document.getElementById("progress").textContent = 
                    "Chunk " + (currentChunk + 1) + " of " + chunks.length + " (" + pct + "%)";
            }}
            
            function updateDisplay() {{
                if (chunks.length === 0) return;
                
                const text = chunks[currentChunk];
                const words = text.split(/(\\s+)/);
                
                let html = "";
                let wordIndex = 0;
                
                for (let i = 0; i < words.length; i++) {{
                    if (words[i].trim()) {{
                        const isCurrent = wordIndex === currentWord;
                        html += '<span class="word' + (isCurrent ? ' current' : '') + '">' + 
                                escapeHtml(words[i]) + '</span>';
                        wordIndex++;
                    }} else {{
                        html += words[i];
                    }}
                }}
                
                document.getElementById("chunkDisplay").innerHTML = html;
                updateProgress();
            }}
            
            function escapeHtml(text) {{
                const div = document.createElement("div");
                div.textContent = text;
                return div.innerHTML;
            }}
            
            function speakChunk() {{
                if (currentChunk >= chunks.length) {{
                    stop();
                    return;
                }}
                
                const text = chunks[currentChunk];
                const words = text.split(/\\s+/).filter(w => w);
                
                // If resuming mid-chunk, slice from current word
                let textToSpeak = text;
                if (currentWord > 0 && currentWord < words.length) {{
                    textToSpeak = words.slice(currentWord).join(" ");
                }}
                
                utterance = new SpeechSynthesisUtterance(textToSpeak);
                utterance.voice = selectedVoice;
                utterance.rate = parseFloat(rateSlider.value);
                
                // Word boundary tracking
                let spokenWordIndex = currentWord;
                utterance.onboundary = function(event) {{
                    if (event.name === "word") {{
                        currentWord = spokenWordIndex;
                        spokenWordIndex++;
                        updateDisplay();
                        savePosition();
                    }}
                }};
                
                utterance.onend = function() {{
                    if (!isPaused) {{
                        currentChunk++;
                        currentWord = 0;
                        savePosition();
                        if (currentChunk < chunks.length) {{
                            speakChunk();
                        }} else {{
                            stop();
                            document.getElementById("progress").textContent = "Finished!";
                        }}
                    }}
                }};
                
                utterance.onerror = function(e) {{
                    console.error("Speech error:", e);
                }};
                
                synth.speak(utterance);
                updateDisplay();
            }}
            
            function play() {{
                if (chunks.length === 0) return;
                
                if (isPaused) {{
                    // Resume
                    isPaused = false;
                    speakChunk();
                }} else {{
                    // Start fresh or from saved position
                    synth.cancel();
                    speakChunk();
                }}
                
                document.getElementById("playBtn").disabled = true;
                document.getElementById("pauseBtn").disabled = false;
                document.getElementById("stopBtn").disabled = false;
            }}
            
            function pause() {{
                isPaused = true;
                synth.cancel();
                savePosition();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
            }}
            
            function stop() {{
                isPaused = false;
                synth.cancel();
                savePosition();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
                document.getElementById("stopBtn").disabled = true;
            }}
            
            function prevChunk() {{
                synth.cancel();
                isPaused = true;
                currentChunk = Math.max(0, currentChunk - 1);
                currentWord = 0;
                savePosition();
                updateDisplay();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
            }}
            
            function nextChunk() {{
                synth.cancel();
                isPaused = true;
                currentChunk = Math.min(chunks.length - 1, currentChunk + 1);
                currentWord = 0;
                savePosition();
                updateDisplay();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
            }}
            
            function resetPosition() {{
                synth.cancel();
                isPaused = false;
                currentChunk = 0;
                currentWord = 0;
                savePosition();
                updateDisplay();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
                document.getElementById("stopBtn").disabled = true;
            }}
            
            // Initialize
            loadPosition();
        </script>
    </body>
    </html>
    """


def main():
    st.title("📖 Auto-Reader")
    st.caption("Upload a document. It reads. You can pause. It remembers where you stopped.")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "epub", "docx", "txt", "md"],
        help="Supported: PDF, EPUB, DOCX, TXT, Markdown"
    )
    
    if uploaded_file:
        # Create document ID from filename for localStorage key
        doc_id = uploaded_file.name.replace(" ", "_").replace(".", "_")
        
        # Extract text
        with st.spinner("Extracting text..."):
            # Write to temp file for processing
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = Path(tmp.name)
            
            try:
                raw_text = extract_text(tmp_path, uploaded_file.type)
                cleaned_text = clean_text(raw_text)
                chunks = chunk_into_paragraphs(cleaned_text)
            finally:
                tmp_path.unlink()  # Clean up temp file
        
        if not chunks:
            st.error("Could not extract any text from this file.")
            return
        
        st.success(f"Loaded **{uploaded_file.name}** — {len(chunks)} chunks, ~{sum(len(c.split()) for c in chunks):,} words")
        
        # Render TTS component
        tts_html = get_tts_component(chunks, doc_id)
        html(tts_html, height=450, scrolling=False)
        
        # Optional: show full text in expander
        with st.expander("View full text"):
            st.text_area(
                "Document content",
                cleaned_text,
                height=300,
                disabled=True,
                label_visibility="collapsed"
            )
    else:
        # Show placeholder component
        placeholder_html = get_tts_component([], "placeholder")
        html(placeholder_html, height=450, scrolling=False)


if __name__ == "__main__":
    main()
