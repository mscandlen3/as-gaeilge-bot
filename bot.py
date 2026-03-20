import os
import tempfile
import logging
from datetime import time
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)
import anthropic

from database import (
    init_db, upsert_user, get_current_unit, set_current_unit,
    mark_unit_complete, get_progress, get_completed_units,
    save_message, load_history,
    save_pronunciation_attempt, get_pronunciation_stats
)
from curriculum import CURRICULUM, get_unit, format_curriculum_overview
from pronunciation import synthesise_irish, build_eval_prompt, transcribe_audio

load_dotenv()
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

user_mode: dict[int, str] = {}
pending_pronunciation: dict[int, str] = {}

SYSTEM_PROMPT = """You are Bríd, a warm and encouraging Irish (Gaeilge) tutor for absolute beginners.
The learner's native language is English. Use the Connacht dialect.

Guidelines:
- Always present Irish first, then English translation
- Include pronunciation hints in brackets e.g. [pron: DYA gwitch]
- Be encouraging; celebrate small wins
- For grammar, explain simply with examples before rules
- Reference real Gaeltacht usage where relevant (Connemara, Donegal, Kerry variants noted)
- Sources to draw on: Buntús Cainte (RTÉ/Gael Linn), gaeilge.ie, teanglann.ie, COGG curriculum

Current mode is passed in the system context per request."""


def get_user(user_id: int) -> dict:
    if user_id not in user_mode:
        user_mode[user_id] = "CHAT"
    return {"mode": user_mode[user_id]}


def claude_reply(user_id: int, user_text: str, extra_system: str = "") -> str:
    history = load_history(user_id, limit=20)
    system = SYSTEM_PROMPT
    if extra_system:
        system += f"\n\n{extra_system}"
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=history,
    )
    return response.content[0].text


def unit_context(user_id: int) -> str:
    unit_num = get_current_unit(user_id)
    unit = get_unit(unit_num)
    if not unit:
        return ""
    return (
        f"Current unit: {unit['unit']} — {unit['title']}\n"
        f"Topics: {', '.join(unit['topics'])}\n"
        f"Vocab targets: {', '.join(unit['vocab_targets'])}\n"
        f"Grammar focus: {unit['grammar']}\n"
        f"Reference source: {unit['reference']}"
    )


async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Welcome & register"),
        BotCommand("curriculum", "View full lesson plan"),
        BotCommand("lesson", "Start current unit lesson"),
        BotCommand("quiz", "Vocabulary quiz for current unit"),
        BotCommand("correct", "Grammar correction mode"),
        BotCommand("translate", "Translate & explain a phrase"),
        BotCommand("chat", "Free conversation in Irish"),
        BotCommand("word", "Word/phrase of the day"),
        BotCommand("pronounce", "Hear & practise a word's pronunciation"),
        BotCommand("progress", "View your progress"),
        BotCommand("next", "Advance to next unit"),
        BotCommand("reset", "Clear history"),
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username or user.first_name)
    unit = get_current_unit(user.id)
    await update.message.reply_text(
        f"☘️ *Fáilte, {user.first_name}!* Welcome to your Irish language journey!\n\n"
        f"You're starting at *Unit {unit}*. Use /curriculum to see the full plan, "
        f"or /lesson to begin straight away!\n\n"
        "Ná bíodh eagla ort — don't be afraid, we'll go step by step! 🌟",
        parse_mode="Markdown"
    )


async def curriculum_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    completed = get_completed_units(user_id)
    current = get_current_unit(user_id)

    lines = ["📚 *Irish Language Curriculum — Absolute Beginner*\n"]
    lines.append("_Sources: Buntús Cainte · gaeilge.ie · COGG · teanglann.ie_\n")
    for u in CURRICULUM:
        status = "✅" if u["unit"] in completed else ("▶️" if u["unit"] == current else "🔒")
        lines.append(f"{status} *Unit {u['unit']}: {u['title']}*")
        lines.append(f"   Topics: {', '.join(u['topics'])}")
        lines.append(f"   Grammar: _{u['grammar']}_")
        lines.append(f"   Source: {u['reference']}\n")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def lesson_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_mode[user_id] = "LESSON"
    ctx = unit_context(user_id)
    unit_num = get_current_unit(user_id)
    unit = get_unit(unit_num)

    prompt = (
        f"Teach Unit {unit_num}: '{unit['title']}'. "
        "Structure the lesson as: 1) Brief intro, 2) Key vocabulary with pronunciation, "
        "3) Example sentences, 4) Grammar note, 5) Short practice exercise for the student."
    )
    save_message(user_id, "user", prompt)
    reply = claude_reply(user_id, prompt, extra_system=f"Mode: LESSON\n{ctx}")
    save_message(user_id, "assistant", reply)
    await update.message.reply_text(reply)


async def quiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_mode[user_id] = "QUIZ"
    ctx = unit_context(user_id)
    unit_num = get_current_unit(user_id)

    prompt = f"Start a 5-question vocabulary quiz for Unit {unit_num}. Ask one question at a time. Wait for my answer before continuing. Keep score and give a final score out of 5 at the end."
    save_message(user_id, "user", prompt)
    reply = claude_reply(user_id, prompt, extra_system=f"Mode: QUIZ\n{ctx}")
    save_message(user_id, "assistant", reply)
    await update.message.reply_text(reply)


async def correct_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_mode[user_id] = "CORRECT"
    await update.message.reply_text(
        "✏️ *Grammar correction mode.*\nWrite something in Irish and I'll correct it and explain any mistakes.",
        parse_mode="Markdown"
    )


async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_mode[user_id] = "TRANSLATE"
    phrase = " ".join(context.args) if context.args else None
    if phrase:
        prompt = f"Translate and explain in detail: '{phrase}'"
        save_message(user_id, "user", prompt)
        reply = claude_reply(user_id, prompt, extra_system="Mode: TRANSLATE")
        save_message(user_id, "assistant", reply)
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text(
            "🔤 *Translate mode.* Send me any English or Irish phrase.",
            parse_mode="Markdown"
        )


async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_mode[user_id] = "CHAT"
    await update.message.reply_text(
        "💬 *Comhrá!* Let's chat in Irish. I'll gently correct mistakes inline.\n\nConas atá tú inniu? (How are you today?)",
        parse_mode="Markdown"
    )


async def word_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = unit_context(user_id)
    prompt = "Give one interesting Irish word or phrase of the day relevant to the learner's current unit. Include: word, pronunciation, meaning, example sentence, and a Gaeltacht cultural note."
    save_message(user_id, "user", prompt)
    reply = claude_reply(user_id, prompt, extra_system=ctx)
    save_message(user_id, "assistant", reply)
    await update.message.reply_text(f"🌟 *Word of the day!*\n\n{reply}", parse_mode="Markdown")


async def pronounce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phrase = " ".join(context.args) if context.args else None

    if not phrase:
        unit = get_unit(get_current_unit(user_id))
        phrase = unit["vocab_targets"][0] if unit else "Dia duit"

    pron_prompt = (
        f"Give a pronunciation guide for the Irish phrase: '{phrase}'\n"
        "Format:\n"
        "- Irish: <phrase>\n"
        "- English phonetics: <how an English speaker would say it, e.g. DEE-ah gwitch>\n"
        "- Meaning: <English translation>\n"
        "- Tips: <1-2 specific sound tips for English speakers>\n"
        "Keep it short and beginner-friendly."
    )
    pron_guide = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": pron_prompt}]
    ).content[0].text

    await update.message.reply_text(
        f"🔊 *Pronunciation practice!*\n\n{pron_guide}\n\n"
        "👂 Now send me a *voice message* saying the phrase and I'll evaluate your pronunciation!",
        parse_mode="Markdown"
    )

    try:
        audio_path = synthesise_irish(phrase)
        with open(audio_path, "rb") as f:
            await update.message.reply_audio(f, title=f"Irish: {phrase}")
        os.unlink(audio_path)
    except Exception as e:
        logging.warning(f"gTTS failed: {e}")
        await update.message.reply_text("_(Audio unavailable for this phrase)_", parse_mode="Markdown")

    pending_pronunciation[user_id] = phrase
    user_mode[user_id] = "PRONOUNCE"


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target = pending_pronunciation.get(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        ogg_path = tmp.name
    await voice_file.download_to_drive(ogg_path)

    try:
        transcription = transcribe_audio(ogg_path)
        os.unlink(ogg_path)

        if not target:
            await update.message.reply_text(
                f"🎙️ I heard: _{transcription}_\n\nUse /pronounce to practise a specific word!",
                parse_mode="Markdown"
            )
            return

        eval_prompt = build_eval_prompt(target, transcription)
        save_message(user_id, "user", eval_prompt)
        evaluation = claude_reply(user_id, eval_prompt, extra_system="Mode: PRONUNCIATION_EVAL")
        save_message(user_id, "assistant", evaluation)

        target_clean = target.lower().strip()
        trans_clean = transcription.lower().strip()
        if target_clean in trans_clean or trans_clean in target_clean:
            score = "good"
        elif any(w in trans_clean for w in target_clean.split()):
            score = "ok"
        else:
            score = "needs_work"

        save_pronunciation_attempt(user_id, target, transcription, score)

        score_emoji = {"good": "🟢", "ok": "🟡", "needs_work": "🔴"}.get(score, "🟡")
        await update.message.reply_text(
            f"🎙️ I heard: _{transcription}_\n{score_emoji}\n\n{evaluation}",
            parse_mode="Markdown"
        )

        pending_pronunciation.pop(user_id, None)
        user_mode[user_id] = "CHAT"

    except Exception as e:
        logging.error(f"Voice handling error: {e}")
        if os.path.exists(ogg_path):
            os.unlink(ogg_path)
        await update.message.reply_text("⚠️ Couldn't process your voice message. Please try again.")


async def progress_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    completed = get_progress(user_id)
    current = get_current_unit(user_id)
    total = len(CURRICULUM)

    if not completed:
        await update.message.reply_text(
            f"📊 *Your Progress*\n\nYou're on Unit {current}/{total}. No units completed yet — start with /lesson!",
            parse_mode="Markdown"
        )
        return

    lines = [f"📊 *Your Progress — Unit {current}/{total}*\n"]
    for p in completed:
        unit = get_unit(p["unit"])
        title = unit["title"] if unit else f"Unit {p['unit']}"
        score_str = f" | Quiz: {p['score']}/5" if p["score"] is not None else ""
        date = p["completed_at"][:10]
        lines.append(f"✅ Unit {p['unit']}: {title}{score_str} _{date}_")

    pct = int(len({p["unit"] for p in completed}) / total * 100)
    lines.append(f"\n*Overall: {pct}% complete*")
    bar = "🟩" * (pct // 10) + "⬜" * (10 - pct // 10)
    lines.append(bar)

    pron_stats = get_pronunciation_stats(user_id)
    if pron_stats:
        good = pron_stats.get("good", 0)
        ok = pron_stats.get("ok", 0)
        needs = pron_stats.get("needs_work", 0)
        total_attempts = good + ok + needs
        lines.append(f"\n🎙️ *Pronunciation attempts:* {total_attempts}")
        lines.append(f"🟢 Good: {good}  🟡 OK: {ok}  🔴 Needs work: {needs}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def next_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = get_current_unit(user_id)
    mark_unit_complete(user_id, current)

    next_unit = current + 1
    if next_unit > len(CURRICULUM):
        await update.message.reply_text(
            "🎉 *Comhghairdeas!* You've completed the full curriculum! Use /progress to review your journey.",
            parse_mode="Markdown"
        )
        return

    set_current_unit(user_id, next_unit)
    unit = get_unit(next_unit)
    await update.message.reply_text(
        f"🎉 Unit {current} marked complete!\n\n"
        f"*Next up — Unit {next_unit}: {unit['title']}*\n"
        f"Topics: {', '.join(unit['topics'])}\n\n"
        "Use /lesson to begin! Ar aghaidh leat! (Forward you go!)",
        parse_mode="Markdown"
    )


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    import sqlite3
    con = sqlite3.connect("irish_bot.db")
    con.execute("DELETE FROM history WHERE user_id=?", (user_id,))
    con.commit()
    con.close()
    user_mode.pop(user_id, None)
    await update.message.reply_text("🔄 Conversation history cleared. Progress is kept. Use /start to continue.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    upsert_user(user_id, update.effective_user.username or "")
    text = update.message.text
    mode = user_mode.get(user_id, "CHAT")
    ctx = unit_context(user_id)

    save_message(user_id, "user", text)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        reply = claude_reply(user_id, text, extra_system=f"Mode: {mode}\n{ctx}")
        save_message(user_id, "assistant", reply)
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")


async def daily_word_job(context: ContextTypes.DEFAULT_TYPE):
    import sqlite3
    con = sqlite3.connect("irish_bot.db")
    rows = con.execute("SELECT user_id FROM users").fetchall()
    con.close()
    for (user_id,) in rows:
        try:
            ctx = unit_context(user_id)
            prompt = "Give one Irish word or phrase of the day relevant to the learner's unit, with pronunciation, meaning, example, and a Gaeltacht note."
            reply = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                system=SYSTEM_PROMPT + f"\n\n{ctx}",
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            await context.bot.send_message(
                chat_id=user_id,
                text=f"☘️ *Word of the day!*\n\n{reply}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Daily word failed for {user_id}: {e}")


def main():
    init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).post_init(set_commands).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("curriculum", curriculum_cmd))
    app.add_handler(CommandHandler("lesson", lesson_cmd))
    app.add_handler(CommandHandler("quiz", quiz_cmd))
    app.add_handler(CommandHandler("correct", correct_cmd))
    app.add_handler(CommandHandler("translate", translate_cmd))
    app.add_handler(CommandHandler("chat", chat_cmd))
    app.add_handler(CommandHandler("word", word_cmd))
    app.add_handler(CommandHandler("pronounce", pronounce_cmd))
    app.add_handler(CommandHandler("progress", progress_cmd))
    app.add_handler(CommandHandler("next", next_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_daily(daily_word_job, time=time(hour=9, minute=0))

    logging.info("☘️ Irish bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
