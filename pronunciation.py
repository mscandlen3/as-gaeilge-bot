import os
import tempfile
from gtts import gTTS
from openai import OpenAI

_openai_client = None


def get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


IRISH_PHONEME_HINTS = {
    "ao": "EE",
    "ai": "A (as in 'hat')",
    "ea": "A (as in 'cat')",
    "io": "IH",
    "ui": "IH",
    "ia": "EE-ah",
    "eo": "OH",
    "bh": "V or W",
    "mh": "V or W",
    "dh": "Y (before e/i) or silent",
    "gh": "Y (before e/i) or silent",
    "fh": "silent",
    "th": "H",
    "ch": "KH (like Scottish 'loch')",
    "ph": "F",
    "sh": "H",
    "nh": "N",
    "lh": "L",
}


def build_pronunciation_guide(irish_text: str) -> str:
    hints = []
    lower = irish_text.lower()
    for pattern, sound in IRISH_PHONEME_HINTS.items():
        if pattern in lower:
            hints.append(f"'{pattern}' → {sound}")
    if hints:
        return "Pronunciation hints: " + " | ".join(hints)
    return ""


def synthesise_irish(text: str) -> str:
    tts = gTTS(text=text, lang="ga", slow=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tmp.name)
    return tmp.name


def transcribe_audio(ogg_path: str) -> str:
    client = get_openai()
    with open(ogg_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            prompt="Irish Gaeilge"  # hints without forcing language
        )
    return result.text.strip()


def build_eval_prompt(target_irish: str, transcribed: str) -> str:
    return f"""The learner was asked to pronounce this Irish phrase:
Target: "{target_irish}"
Whisper transcribed their attempt as: "{transcribed}"

Please evaluate their pronunciation:
1. How close is the transcription to the target? (note: Whisper may not spell Irish perfectly)
2. Identify specific sounds they likely got right and wrong
3. Give clear tips using English phonetic approximations (e.g. "the 'bh' sounds like 'V'")
4. End with an encouraging message and the correct pronunciation guide

Be understanding — Irish pronunciation is genuinely difficult for beginners!"""
