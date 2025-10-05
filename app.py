# app.py
# Hindi/Marathi Text to Speech with improved naturalness (no API keys)
# Combines edge-tts + pyttsx3 (offline) + audio smoothing

import streamlit as st
import asyncio
import edge_tts
import pyttsx3
from io import BytesIO
from datetime import datetime
from pydub import AudioSegment, effects
import tempfile

st.set_page_config(page_title="🎙️ Realistic Hindi/Marathi TTS", page_icon="🎧", layout="centered")

st.title("🎧 Hindi / Marathi Text → Voice (Free & Realistic)")
st.caption("Enhanced realism using neural edge-tts or offline pyttsx3, no API key required.")

lang = st.selectbox("Language", ["Hindi (hi-IN)", "Marathi (mr-IN)"])
engine_choice = st.radio("Voice Engine", ["Edge-TTS (Online Neural)", "Offline (pyttsx3)"])
text = st.text_area("Enter text", height=200, placeholder="यहाँ हिंदी में लिखें... / येथे मराठी मजकूर लिहा...")
rate = st.slider("Speed (Rate)", -50, 50, 5)
pitch = st.slider("Pitch (younger voice = higher)", -8, 8, 2)

def normalize_audio(audio_bytes: bytes) -> bytes:
    """Normalize volume for smoother playback"""
    audio = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
    normalized = effects.normalize(audio)
    out_buf = BytesIO()
    normalized.export(out_buf, format="mp3")
    return out_buf.getvalue()

async def pick_female_voice(locale_code: str):
    voices = await edge_tts.VoicesManager.create()
    female = [v for v in voices.voices if v["Locale"] == locale_code and v["Gender"] == "Female"]
    neural = [v for v in female if "Neural" in v["ShortName"]]
    return (neural or female or voices.voices)[0]["ShortName"]

async def synth_edge_tts(text, locale, rate, pitch):
    voice = await pick_female_voice(locale)
    rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
    pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}st"
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str, pitch=pitch_str)
    out = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            out.write(chunk["data"])
    return out.getvalue()

def synth_pyttsx3(text, lang):
    """Offline fallback using system voice (no internet)."""
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    # Try selecting Indian female voice if available
    for v in voices:
        if ("female" in v.name.lower() or "zira" in v.name.lower()) and ("hi" in v.id.lower() or "marathi" in v.id.lower()):
            engine.setProperty("voice", v.id)
            break
    engine.setProperty("rate", 170)  # slow, clear tone
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    engine.save_to_file(text, temp_file.name)
    engine.runAndWait()
    with open(temp_file.name, "rb") as f:
        data = f.read()
    return data

def filename(prefix="voice"):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

if st.button("Generate 🎙️", use_container_width=True):
    if not text.strip():
        st.error("Please enter some text first.")
    else:
        locale = "hi-IN" if lang.startswith("Hindi") else "mr-IN"
        st.info(f"Generating voice using {engine_choice}...")
        audio_bytes = None
        try:
            if engine_choice == "Edge-TTS (Online Neural)":
                audio_bytes = asyncio.run(synth_edge_tts(text, locale, rate, pitch))
            else:
                audio_bytes = synth_pyttsx3(text, locale)
            audio_bytes = normalize_audio(audio_bytes)
            st.success("✅ Done! Play or download below:")
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                "⬇️ Download MP3",
                data=audio_bytes,
                file_name=filename("tts"),
                mime="audio/mpeg"
            )
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")
st.caption("💡 Tip: Use Edge-TTS for smoother, more natural voice (needs internet). Use Offline if network restricted.")
