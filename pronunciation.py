import os
import tempfile
from gtts import gTTS
from faster_whisper import WhisperModel

_whisper_model = None


def get_whisper() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        # cpu mode, int8 for low memory usage on free tier
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


# ── Pronunciation guide ───────────────────────────────────────────────────────
# Irish phonemes mapped to English approximations for absolute beginners.
# Based on Buntús Cainte pronunciation notes and SoundOut Irish guides.

IRISH_PHONEME_HINTS = {
    # Vowels
    "ao": "EE",
    "ai": "A (as in 'hat')",
    "ea": "A (as in 'cat')",
    "io": "IH",
    "ui": "IH",
    "ia": "EE-ah",
    "eo": "OH",
    # Consonants
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
    """
    Returns a plain-English pronunciation guide for an Irish word/phrase.
    Uses Claude for nuanced guidance — this is a fallback rule-based hint.
    """
    hints = []
    lower = irish_text.lower()
    for pattern, sound in IRISH_PHONEME_HINTS.items():
        if pattern in lower:
            hints.append(f"'{pattern}' → {sound}")
    if hints:
        return "Pronunciation hints: " + " | ".join(hints)
    return ""


# ── Text-to-Speech ────────────────────────────────────────────────────────────

def synthesise_irish(text: str) -> str:
    """
    Generate an Irish audio file using gTTS.
    Returns path to a temp .mp3 file.
    Note: gTTS uses 'ga' (Irish/Gaeilge) locale.
    """
    tts = gTTS(text=text, lang="ga", slow=True)  # slow=True helps learners
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tmp.name)
    return tmp.name


# ── Speech-to-Text ────────────────────────────────────────────────────────────

def transcribe_audio(ogg_path: str) -> str:
    model = get_whisper()
    segments, _ = model.transcribe(ogg_path, language="ga")
    return " ".join(s.text for s in segments).strip()


def transcribe_audio_english(ogg_path: str) -> str:
    model = get_whisper()
    segments, _ = model.transcribe(ogg_path)
    return " ".join(s.text for s in segments).strip()
    

# ── Pronunciation evaluation prompt ──────────────────────────────────────────

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
