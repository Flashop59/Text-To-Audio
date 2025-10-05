# app.py
# Streamlit TTS for Hindi/Marathi with realistic young female voice
# Primary engine: edge-tts (neural, no API key). Optional fallback: gTTS.
# Play in-browser + Download as MP3.

import streamlit as st
import asyncio
import edge_tts
from io import BytesIO
from datetime import datetime
from typing import Optional

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False


st.set_page_config(page_title="Hindi/Marathi Text → Realistic Female Voice", page_icon="🎤", layout="centered")

st.title("🎤 Text → Speech (Hindi / Marathi) – Realistic Female Voice")
st.caption("Neural voice via edge-tts. Auto-picks a young-sounding female voice for your language. Downloadable MP3.")

# ---------------------------
# UI Controls
# ---------------------------
lang = st.selectbox("Language", ["Hindi (hi-IN)", "Marathi (mr-IN)"])
text = st.text_area(
    "Paste your Hindi or Marathi text here",
    height=200,
    placeholder="यहाँ हिंदी में अपना टेक्स्ट पेस्ट करें…\nकिंवा येथे तुमचा मराठी मजकूर पेस्ट करा…",
)

col1, col2, col3 = st.columns(3)
with col1:
    rate = st.slider("Speed (rate)", -50, 50, 0, help="Negative = slower, Positive = faster (edge-tts)")
with col2:
    pitch = st.slider("Pitch (semitones)", -8, 8, 0, help="Lower/raise pitch to sound younger/older")
with col3:
    fallback = st.checkbox("Enable gTTS fallback", value=True, help="Uses Google TTS if neural engine fails")

hint = st.caption("Tip: Slightly **faster** rate (+5 to +12) and **higher** pitch (+1 to +3) often feel like a ~23-year-old voice.")

generate = st.button("Generate Audio", type="primary", use_container_width=True)


# ---------------------------
# Helpers
# ---------------------------
def filename_base(prefix: str = "tts") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}"

async def pick_female_voice(locale_code: str) -> Optional[str]:
    """
    Dynamically pick a female neural voice for the given locale (e.g., 'hi-IN' or 'mr-IN').
    """
    voices_manager = await edge_tts.VoicesManager.create()
    # Prefer Neural female voices
    female_candidates = [v for v in voices_manager.voices if v.get("Locale") == locale_code and v.get("Gender") == "Female"]
    # Further prefer 'Neural' voices in ShortName (most are Neural anyway)
    female_neural = [v for v in female_candidates if "Neural" in v.get("ShortName", "")]
    chosen = (female_neural or female_candidates)
    if not chosen:
        return None
    # Heuristic: prefer names often perceived as younger/bright (sorted by locale default order)
    # But in practice, any female Neural voice should sound modern and natural.
    return chosen[0]["ShortName"]

async def synth_edge_tts(text: str, locale: str, rate_pct: int = 0, pitch_semitones: int = 0) -> bytes:
    """
    Synthesize using edge-tts and return MP3 bytes.
    """
    voice_name = await pick_female_voice(locale)
    if not voice_name:
        raise RuntimeError(f"No suitable female voice found for locale {locale}.")

    # edge-tts accepts rate like '+10%' and pitch like '+2Hz' or '+2st' (semitones)
    rate_str = f"{'+' if rate_pct >= 0 else ''}{rate_pct}%"
    pitch_str = f"{'+' if pitch_semitones >= 0 else ''}{pitch_semitones}st"

    communicate = edge_tts.Communicate(text, voice=voice_name, rate=rate_str, pitch=pitch_str)
    audio_buffer = BytesIO()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    return audio_buffer.getvalue()

def synth_gtts(text: str, lang_code: str) -> bytes:
    """
    Simple fallback using gTTS (female-ish default voice).
    """
    if not HAS_GTTS:
        raise RuntimeError("gTTS not installed. Run `pip install gTTS` or disable fallback.")
    tts = gTTS(text=text, lang=lang_code)
    out = BytesIO()
    tts.write_to_fp(out)
    return out.getvalue()


# ---------------------------
# Main action
# ---------------------------
if generate:
    if not text.strip():
        st.error("Please paste some text first.")
    else:
        locale = "hi-IN" if lang.startswith("Hindi") else "mr-IN"
        lang_code_for_gtts = "hi" if locale == "hi-IN" else "mr"

        with st.spinner("Creating neural speech…"):
            audio_bytes = None
            error_msg = None

            # Try edge-tts first (neural, realistic)
            try:
                audio_bytes = asyncio.run(synth_edge_tts(text, locale, rate, pitch))
                engine_used = f"edge-tts (Neural, {locale})"
            except Exception as e:
                error_msg = str(e)

            # Fallback to gTTS if enabled and needed
            if audio_bytes is None and fallback:
                try:
                    with st.spinner("Neural engine unavailable. Falling back to gTTS…"):
                        audio_bytes = synth_gtts(text, lang_code_for_gtts)
                        engine_used = f"gTTS fallback ({lang_code_for_gtts})"
                except Exception as e:
                    error_msg = f"{error_msg or ''} | Fallback error: {e}"

            if audio_bytes:
                st.success(f"Done! Engine: {engine_used}")
                st.audio(audio_bytes, format="audio/mp3")

                base = filename_base("voice_hi" if locale == "hi-IN" else "voice_mr")
                fname = f"{base}.mp3"
                st.download_button(
                    "Download MP3",
                    data=audio_bytes,
                    file_name=fname,
                    mime="audio/mpeg",
                    use_container_width=True
                )
            else:
                st.error("Sorry, I couldn't generate the audio.")
                if error_msg:
                    with st.expander("Show technical details"):
                        st.code(error_msg)

# Footer
st.markdown(
    """
---
**Notes**
- The app auto-selects a **female neural voice** for a natural, realistic tone.  
- Use **Pitch** (+1 to +3) and **Speed** (+5 to +12) to emulate a youthful (~23) vibe.  
- If your network blocks the neural service, enable the **gTTS fallback**.
    """
)
