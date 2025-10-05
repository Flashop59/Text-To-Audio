# app.py
# Streamlit app: Convert Hindi/Marathi text into realistic 23-year-old female voice (playable + downloadable)
# Works directly on Streamlit Cloud — no API key needed.

import streamlit as st
import asyncio
import edge_tts
from io import BytesIO
from datetime import datetime

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False


st.set_page_config(page_title="🎤 Text to Voice - Hindi/Marathi", page_icon="🎧", layout="centered")

st.title("🎧 Hindi / Marathi Text to Voice")
st.caption("Realistic young female voice (~23 y/o). Play or download your audio instantly.")

# --- Input UI ---
lang = st.selectbox("Select Language", ["Hindi (hi-IN)", "Marathi (mr-IN)"])
text = st.text_area(
    "Enter or paste your text below 👇",
    placeholder="यहाँ हिंदी में टाइप करें... / येथे मराठी मजकूर टाइप करा...",
    height=200
)
rate = st.slider("Voice Speed (rate)", -50, 50, 0)
pitch = st.slider("Voice Pitch (younger = higher)", -8, 8, 2)
fallback = st.checkbox("Enable gTTS fallback", value=True)

# --- Helper functions ---
def timestamped_filename(prefix="voice") -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

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

def synth_gtts(text, lang_code):
    if not HAS_GTTS:
        raise RuntimeError("gTTS not installed.")
    tts = gTTS(text=text, lang=lang_code)
    out = BytesIO()
    tts.write_to_fp(out)
    return out.getvalue()

# --- Generate ---
if st.button("Generate Audio 🎙️", use_container_width=True):
    if not text.strip():
        st.error("Please enter some text first!")
    else:
        locale = "hi-IN" if lang.startswith("Hindi") else "mr-IN"
        lang_code = "hi" if locale == "hi-IN" else "mr"

        with st.spinner("Generating voice..."):
            try:
                audio_bytes = asyncio.run(synth_edge_tts(text, locale, rate, pitch))
                st.success("✅ Neural voice generated!")
            except Exception as e:
                if fallback:
                    st.warning(f"Edge TTS failed ({e}). Trying gTTS fallback...")
                    try:
                        audio_bytes = synth_gtts(text, lang_code)
                        st.success("✅ gTTS fallback successful!")
                    except Exception as e2:
                        st.error(f"Both engines failed: {e2}")
                        audio_bytes = None
                else:
                    st.error(f"Neural TTS failed: {e}")
                    audio_bytes = None

        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                label="⬇️ Download MP3",
                data=audio_bytes,
                file_name=timestamped_filename("tts"),
                mime="audio/mpeg"
            )

st.markdown("---")
st.caption("💡 Tip: Use slightly faster (+8) and higher pitch (+2~+3) for a youthful 23-year-old tone.")
