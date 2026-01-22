# Auto-Reader v1.0.2
# File-to-speech with position persistence using edge-tts.

import asyncio
import base64
import hashlib
import json
import tempfile
from pathlib import Path

import edge_tts
import streamlit as st
from streamlit.components.v1 import html

from extractors import extract_text, clean_text, chunk_into_paragraphs

VERSION = "1.0.2"
VOICE = "en-US-JennyNeural"  # Female US English neural voice

st.set_page_config(
    page_title="Auto-Reader",
    page_icon="📖",
    layout="centered",
)

st.markdown("""
<style>
    .stApp { max-width: 800px; margin: 0 auto; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


async def generate_audio(text: str) -> bytes:
    """Generate MP3 audio from text using edge-tts."""
    communicate = edge_tts.Communicate(text, VOICE)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data


def get_audio_base64(text: str) -> str:
    """Generate audio and return as base64 string."""
    audio_bytes = asyncio.run(generate_audio(text))
    return base64.b64encode(audio_bytes).decode("utf-8")


def get_player_component(chunks: list[str], doc_id: str, audio_cache: dict[int, str]) -> str:
    """
    HTML/JS component with HTML5 audio player.
    Pre-generated audio chunks with native pause/play controls.
    Position persisted to localStorage.
    """
    audio_json = json.dumps(audio_cache)
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
            input[type="range"] {{
                background: #262730;
                border: 1px solid #444;
                border-radius: 4px;
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
                <label for="rate">Speed:</label>
                <input type="range" id="rate" min="0.5" max="2" step="0.1" value="1">
                <span id="rateVal">1.0x</span>
            </div>
        </div>
        
        <div class="progress" id="progress">Ready</div>
        
        <div class="chunk-display" id="chunkDisplay">
            Press Play to begin reading.
        </div>
        
        <div class="nav-buttons">
            <button class="nav-btn" onclick="prevChunk()">← Previous</button>
            <button class="nav-btn" onclick="nextChunk()">Next →</button>
            <button class="nav-btn" onclick="resetPosition()">↺ Reset</button>
        </div>
        
        <audio id="audioPlayer" style="display:none;"></audio>
        
        <script>
            const DOC_ID = "{doc_id}";
            const STORAGE_KEY = "autoreader_" + DOC_ID;
            const chunks = {chunks_json};
            const audioData = {audio_json};
            
            const audio = document.getElementById("audioPlayer");
            let currentChunk = 0;
            let currentTime = 0;
            let isPlaying = false;
            
            function loadPosition() {{
                const saved = localStorage.getItem(STORAGE_KEY);
                if (saved) {{
                    const pos = JSON.parse(saved);
                    currentChunk = Math.min(pos.chunk || 0, chunks.length - 1);
                    currentTime = pos.time || 0;
                }}
                updateDisplay();
            }}
            
            function savePosition() {{
                localStorage.setItem(STORAGE_KEY, JSON.stringify({{
                    chunk: currentChunk,
                    time: audio.currentTime || 0
                }}));
            }}
            
            const rateSlider = document.getElementById("rate");
            const rateVal = document.getElementById("rateVal");
            rateSlider.oninput = function() {{
                rateVal.textContent = parseFloat(this.value).toFixed(1) + "x";
                audio.playbackRate = parseFloat(this.value);
                localStorage.setItem(STORAGE_KEY + "_rate", this.value);
            }};
            
            const savedRate = localStorage.getItem(STORAGE_KEY + "_rate");
            if (savedRate) {{
                rateSlider.value = savedRate;
                rateVal.textContent = parseFloat(savedRate).toFixed(1) + "x";
            }}
            
            function updateProgress() {{
                const pct = Math.round(((currentChunk + 1) / chunks.length) * 100);
                document.getElementById("progress").textContent = 
                    "Chunk " + (currentChunk + 1) + " of " + chunks.length + " (" + pct + "%)";
            }}
            
            function updateDisplay() {{
                if (chunks.length === 0) return;
                document.getElementById("chunkDisplay").textContent = chunks[currentChunk];
                updateProgress();
            }}
            
            // Event handlers - set once at initialization
            audio.addEventListener("ended", function() {{
                if (isPlaying) {{
                    currentChunk++;
                    currentTime = 0;
                    savePosition();
                    if (currentChunk < chunks.length) {{
                        updateDisplay();
                        loadAndPlayChunk(0);
                    }} else {{
                        stop();
                        document.getElementById("progress").textContent = "Finished!";
                    }}
                }}
            }});
            
            audio.addEventListener("timeupdate", savePosition);
            
            function loadAndPlayChunk(startTime = 0) {{
                // Update display first
                updateDisplay();
                
                if (currentChunk >= chunks.length) {{
                    stop();
                    document.getElementById("progress").textContent = "Finished!";
                    return;
                }}
                
                const b64 = audioData[currentChunk];
                if (!b64) {{
                    console.error("No audio for chunk", currentChunk);
                    return;
                }}
                
                audio.src = "data:audio/mp3;base64," + b64;
                audio.playbackRate = parseFloat(rateSlider.value);
                
                audio.onloadedmetadata = function() {{
                    if (startTime > 0 && startTime < audio.duration) {{
                        audio.currentTime = startTime;
                    }}
                    audio.play();
                }};
            }}
            
            function play() {{
                if (chunks.length === 0) return;
                
                isPlaying = true;
                
                if (audio.paused && audio.src && audio.src.startsWith("data:")) {{
                    audio.play();
                }} else {{
                    loadAndPlayChunk(currentTime);
                }}
                
                document.getElementById("playBtn").disabled = true;
                document.getElementById("pauseBtn").disabled = false;
                document.getElementById("stopBtn").disabled = false;
            }}
            
            function pause() {{
                isPlaying = false;
                audio.pause();
                savePosition();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
            }}
            
            function stop() {{
                isPlaying = false;
                audio.pause();
                audio.currentTime = 0;
                currentTime = 0;
                savePosition();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
                document.getElementById("stopBtn").disabled = true;
            }}
            
            function prevChunk() {{
                isPlaying = false;
                audio.pause();
                currentChunk = Math.max(0, currentChunk - 1);
                currentTime = 0;
                savePosition();
                updateDisplay();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
            }}
            
            function nextChunk() {{
                isPlaying = false;
                audio.pause();
                currentChunk = Math.min(chunks.length - 1, currentChunk + 1);
                currentTime = 0;
                savePosition();
                updateDisplay();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
            }}
            
            function resetPosition() {{
                isPlaying = false;
                audio.pause();
                audio.src = "";
                currentChunk = 0;
                currentTime = 0;
                savePosition();
                updateDisplay();
                
                document.getElementById("playBtn").disabled = false;
                document.getElementById("pauseBtn").disabled = true;
                document.getElementById("stopBtn").disabled = true;
            }}
            
            loadPosition();
        </script>
    </body>
    </html>
    """


def main():
    st.title("Auto-Reader")
    st.caption(f"v{VERSION}")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "epub", "docx", "txt", "md"],
        help="Supported: PDF, EPUB, DOCX, TXT, Markdown"
    )
    
    if uploaded_file:
        doc_id = hashlib.md5(uploaded_file.name.encode()).hexdigest()[:12]
        
        with st.spinner("Extracting text..."):
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = Path(tmp.name)
            
            try:
                raw_text = extract_text(tmp_path, uploaded_file.type)
                cleaned_text = clean_text(raw_text)
                chunks = chunk_into_paragraphs(cleaned_text)
            finally:
                tmp_path.unlink()
        
        if not chunks:
            st.error("Could not extract any text from this file.")
            return
        
        audio_cache = {}
        progress_bar = st.progress(0, text="Generating audio...")
        
        for i, chunk in enumerate(chunks):
            audio_cache[i] = get_audio_base64(chunk)
            progress_bar.progress((i + 1) / len(chunks), text=f"Generating audio... {i + 1}/{len(chunks)}")
        
        progress_bar.empty()
        
        word_count = sum(len(c.split()) for c in chunks)
        st.success(f"Loaded **{uploaded_file.name}** — {len(chunks)} chunks, ~{word_count:,} words")
        
        player_html = get_player_component(chunks, doc_id, audio_cache)
        html(player_html, height=400, scrolling=False)
        
        with st.expander("View full text"):
            st.text_area(
                "Document content",
                cleaned_text,
                height=300,
                disabled=True,
                label_visibility="collapsed"
            )
    else:
        html(get_player_component([], "placeholder", {}), height=400, scrolling=False)


if __name__ == "__main__":
    main()
