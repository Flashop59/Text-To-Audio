import streamlit as st
import asyncio
import edge_tts
from io import BytesIO
from datetime import datetime

# Optional fallback
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

st.set_page_config(page_title="🎤 Text to Voice (Hindi/Marathi)", page_icon="🎧", layout="centered")

st.title("🎧 Hindi / Marathi Text to Speech")
st.caption("Realistic young female (~23y) neural voice with adjustable speed & pitch.")

# --- Inputs ---
lang = st.selectbox("Select Language", ["Hindi (hi-IN)", "Marathi (mr-IN)"])
text = st.text_area(
    "Enter or paste your text below 👇",
    placeholder="यहाँ हिंदी में टाइप करें... / येथे मराठी मजकूर टाइप करा...",
    height=200
)
speed = st.slider("Speed (%)", -50, 50, 0, help="Negative = slower, Positive = faster")
pitch = st.slider("Pitch (semitones)", -8, 8, 0, help="Positive = younger voice, Negative = deeper")
fallback = st.checkbox("Enable gTTS fallback (for offline backup)", value=True)

# --- Helpers ---
def get_filename():
    return f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

async def pick_female_voice(locale_code: str):
    voices = await edge_tts.VoicesManager.create()
    female = [v for v in voices.voices if v["Locale"] == locale_code and v["Gender"] == "Female"]
    neural = [v for v in female if "Neural" in v["ShortName"]]
    if neural:
        return neural[0]["ShortName"]
    elif female:
        return female[0]["ShortName"]
    else:
        return voices.voices[0]["ShortName"]

async def synth_edge_tts(text, locale, speed, pitch):
    voice = await pick_female_voice(locale)

    # Properly formatted modifiers for edge-tts
    rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
    pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}st"

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate_str,
        pitch=pitch_str
    )

    audio = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.write(chunk["data"])
    return audio.getvalue()

def synth_gtts(text, lang_code):
    if not HAS_GTTS:
        raise RuntimeError("gTTS not installed.")
    tts = gTTS(text=text, lang=lang_code)
    out = BytesIO()
    tts.write_to_fp(out)
    return out.getvalue()

# --- Main Button ---
if st.button("Generate 🎙️", use_container_width=True):
    if not text.strip():
        st.error("Please enter some text first.")
    else:
        locale = "hi-IN" if lang.startswith("Hindi") else "mr-IN"
        lang_code = "hi" if locale == "hi-IN" else "mr"

        with st.spinner("Generating neural speech..."):
            audio_bytes = None
            try:
                audio_bytes = asyncio.run(synth_edge_tts(text, locale, speed, pitch))
                st.success("✅ Done! Neural voice generated successfully.")
            except Exception as e:
                st.warning(f"⚠️ Neural engine error: {e}")
                if fallback:
                    try:
                        st.info("Trying gTTS fallback...")
                        audio_bytes = synth_gtts(text, lang_code)
                        st.success("✅ gTTS fallback succeeded!")
                    except Exception as e2:
                        st.error(f"Fallback failed too: {e2}")

        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                "⬇️ Download MP3",
                data=audio_bytes,
                file_name=get_filename(),
                mime="audio/mpeg"
            )

st.markdown("---")
st.caption("💡 Tip: Try **Speed +10** and **Pitch +2** for a more youthful, natural 23-year-old sound.")
