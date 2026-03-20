def synthesise_irish(text: str) -> str:
    tts = gTTS(text=text, lang="en", slow=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tmp.name)
    return tmp.name


def transcribe_audio(ogg_path: str) -> str:
    client = get_openai()
    with open(ogg_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            prompt="Irish Gaeilge"
        )
    return result.text.strip()


def build_eval_prompt(target_irish: str, transcribed: str) -> str:
    return f"""The learner is an absolute beginner trying to pronounce this Irish phrase:
Target: "{target_irish}"
Whisper transcribed their attempt as: "{transcribed}"

Important context:
- Irish pronunciation is extremely difficult for English speakers
- Whisper was not trained heavily on Irish so its transcription may be inaccurate
- Even a rough approximation deserves praise
- This person is just starting out and needs encouragement above all else

Please respond warmly:
1. Start with genuine praise for their attempt — find something positive no matter what
2. Give 1-2 gentle, specific tips (not a long list)
3. Use simple English phonetic guides e.g. "the 'bh' sounds like 'V'"
4. End with an enthusiastic encouraging message in both English and Irish
5. Keep the whole response short and friendly — this is not a strict exam!

Never be harsh, never list many errors at once. One small improvement at a time."""
