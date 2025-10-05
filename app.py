# app.py
# Hindi/Marathi Text to Speech with improved tone (no API keys, fully free)
# Works on Streamlit Cloud – no pydub, no pyaudio required

import streamlit as st
import asyncio
import edge_tts
import pyttsx3
from io import BytesIO
from datetime import datetime
import tempfile

st.set_page_config(page_title="🎙️ Hindi/Marathi Text to Speech", page_icon="🎧", layout="centered")

st.title("🎧 Hindi / Marathi Text → Voice (Free & Realistic)")
st.caption("No API key needed — choose online neural or offline TTS engine.")

lang = st.selectbox("Language", ["Hindi (hi-IN)", "Marathi (mr-IN)"])
engine_choice = st.radio("Voice Engine", ["Edge-TTS (Online Neural)", "Offline (pyttsx3)"])
text = st.text_area("Enter text", height=200, placeholder="यहाँ हिंदी में लिखें... / येथे मराठी मजकूर लिहा...")
rate = st.slider("Speed (Rate)", -50, 50, 5)
pitch = st.slider("Pitch (younger = higher)", -8, 8, 2)

# Helper functions
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
    """Offline fallback using system voice (runs locally only)."""
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    for v in voices:
        if ("female" in v.name.lower() or "zira" in v.name.lower()):
            engine.setProperty("voice", v.id)
            break
    engine.setProperty("rate", 170)
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    engine.save_to_file(text, temp_file.name)
    engine.runAndWait()
    with open(temp_file.name, "rb") as f:
        data = f.read()
    return data

def filename(prefix="voice"):
    from datetime import datetime
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

# Generate audio
if st.button("Generate 🎙️", use_container_width=True):
    if not text.strip():
        st.error("Please enter some text first.")
    else:
        locale = "hi-IN" if lang.startswith("Hindi") else "mr-IN"
        st.info(f"Generating using {engine_choice} ...")
        audio_bytes = None
        try:
            if engine_choice == "Edge-TTS (Online Neural)":
                audio_bytes = asyncio.run(synth_edge_tts(text, locale, rate, pitch))
            else:
                audio_bytes = synth_pyttsx3(text, locale)
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
st.caption("💡 Tip: Use Edge-TTS for smoother voice (requires internet). Offline voice works locally but not on Streamlit Cloud.")
