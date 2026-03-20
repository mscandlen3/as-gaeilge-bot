import os
import tempfile
from gtts import gTTS

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
    """Generate Irish audio using gTTS. Returns path to temp .mp3 file."""
    tts = gTTS(text=text, lang="ga", slow=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tmp.name)
    return tmp.name


def build_eval_prompt(target_irish: str, transcribed: str) -> str:
    return ""
