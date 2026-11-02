import asyncio
import json
import logging
import os
import sqlite3
import random
import subprocess
from typing import Dict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Message,
)
from aiogram.client.session.aiohttp import AiohttpSession

# --- CONFIG ---
API_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = "scores.db"
logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
router = Router()
dp.include_router(router)

# Функция для автоматической нарезки круглого видео "на лету" через FFmpeg
def cut_video_note(input_file: str, output_file: str, start_sec: int, end_sec: int):
    duration = end_sec - start_sec
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", input_file,
        "-t", str(duration),
        "-vf", "crop=in_h:in_h,scale=400:400",
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        output_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

with open("songs.json", encoding="utf-8") as f:
    SONGS = json.load(f)

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Play")], [KeyboardButton(text="My score")]],
    resize_keyboard=True
)
next_fragment_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Next")], [KeyboardButton(text="Play"), KeyboardButton(text="My score")]],
    resize_keyboard=True
)
pause_choice_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Continue this song")], [KeyboardButton(text="Choose another song")]],
    resize_keyboard=True
)

current_question: Dict[int, Dict[str, object]] = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, score INTEGER NOT NULL DEFAULT 0)")
    conn.commit()
    conn.close()

def get_user_score(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO users (user_id, score) VALUES (?, 0)", (user_id,))
        conn.commit()
        score = 0
    else:
        score = int(row[0])
    conn.close()
    return score

def add_score(user_id: int, points: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()
    return get_user_score(user_id)

def get_song_by_id(song_id: str) -> dict | None:
    return next((s for s in SONGS if s["id"] == song_id), None)

def get_words_keyboard(words: list, selected_indices: list) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for idx, word in enumerate(words):
        if idx in selected_indices:
            order = selected_indices.index(idx) + 1
            label = f"✅{order}"
        else:
            label = word
        row.append(InlineKeyboardButton(text=label, callback_data=f"word:{idx}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="⬅️ Убрать последнее слово", callback_data="word_undo"),
        InlineKeyboardButton(text="Сбросить всё 🔄", callback_data="word_reset"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_fragment(message: Message, user_id: int):
    data = current_question.get(user_id)
    if not data:
        return await show_songs_menu(message, user_id)

    song = get_song_by_id(data["song_id"])
    idx = data["fragment_index"]
    fragment = song["fragments"][idx]

    input_path = os.path.join("audio", fragment["file"])
    if not os.path.exists(input_path):
        return await message.answer(f"⚠️ Базовый файл {fragment['file']} не найден в папке audio")

    if "start" in fragment and "end" in fragment:
        output_filename = f"cut_{data['song_id']}_{idx}.mp4"
        output_path = os.path.join("audio", output_filename)
        
        if not os.path.exists(output_path):
            await message.answer("🔄 Подготавливаю видео-кружочек...")
            cut_video_note(input_path, output_path, fragment["start"], fragment["end"])
        
        target_file = output_path
    else:
        target_file = input_path

    if os.path.exists(target_file):
        await message.bot.send_video_note(chat_id=message.chat.id, video_note=FSInputFile(target_file))
    else:
        await message.answer("⚠️ Ошибка обработки видео.")
        return

    if fragment.get("type") == "word_order":
        full_text = fragment["text"]
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        
        # Защита от повторного перемешивания при Reset: берем уже сохраненную строку или выбираем новую
        if "target_line" not in data:
            target_line = random.choice(lines)
            data["target_line"] = target_line
        else:
            target_line = data["target_line"]

        clean_text = target_line.replace(",", "").replace(".", "").replace("(", "").replace(")", "")
        words = clean_text.split()

        indices = list(range(len(words)))
        random.seed(user_id + idx)
        random.shuffle(indices)

        data["target_line"] = target_line
        data["words_list"] = words
        data["shuffled_indices"] = indices
        data["selected_indices"] = []
        data["current_assembled"] = ""
        data["word_order_header"] = "🧩 **Послушай кружочек и собери строчку!** Нажимай на слова по порядку:"

        kb = get_words_keyboard([words[i] for i in indices], data["selected_indices"])
        await message.answer(
            f"{data['word_order_header']}\n\n**Твоя фраза:** (пока пусто)",
            reply_markup=kb,
            parse_mode="Markdown",
        )
    else:
        await message.answer(fragment["text"])

@router.callback_query(F.data.startswith("word:"))
async def cb_word_click(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in current_question:
        return await cb.answer()

    data = current_question[user_id]
    clicked_idx = int(cb.data.split(":")[1])
    
    if clicked_idx in data["selected_indices"]:
        return await cb.answer()

    data["selected_indices"].append(clicked_idx)
    current_words = [data["words_list"][data["shuffled_indices"][i]] for i in data["selected_indices"]]
    data["current_assembled"] = " ".join(current_words)
    
    song = get_song_by_id(data["song_id"])
    fragment = song["fragments"][data["fragment_index"]]
    
    if len(data["selected_indices"]) == len(data["words_list"]):
        assembled = data["current_assembled"]
        clean_target = (
            data["target_line"]
            .replace(",", "")
            .replace(".", "")
            .replace("(", "")
            .replace(")", "")
        )
        correct = " ".join(clean_target.split())

        if assembled.lower().strip() != correct.lower().strip():
            data["selected_indices"] = []
            data["current_assembled"] = ""

            kb = get_words_keyboard(
                [data["words_list"][i] for i in data["shuffled_indices"]],
                data["selected_indices"],
            )
            display_text = (
                f"❌ Неверный порядок, попробуй ещё раз\n\n"
                f"{data['word_order_header']}\n\n"
                f"**Твоя фраза:** (пока пусто)"
            )
            try:
                await cb.message.edit_text(display_text, reply_markup=kb, parse_mode="Markdown")
            except Exception:
                pass
            await cb.answer()
            return

        score = add_score(user_id, 10)
        trans = fragment.get("translation_ru", "")

        await cb.message.edit_text(
            f"✅ **Отлично сработано!**\n\n📝 Строчка: *{data['target_line']}*\n\n"
            f"Твой счет: {score} ⭐\nПеревод: {trans}",
            parse_mode="Markdown",
        )

        # Очищаем сохраненную строку для следующего раунда
        if "target_line" in data:
            del data["target_line"]

        if data["fragment_index"] >= len(song["fragments"]) - 1:
            del current_question[user_id]
            await cb.message.answer("🔥 **Песня полностью разобрана! Превосходный результат!**", reply_markup=main_kb)
            # ИСПРАВЛЕНО: раньше сюда передавался cb.message, из-за чего
            # get_user_score() считал очки бота, а не игрока, и счёт показывался как 0.
            await show_songs_menu(cb.message, user_id)
        else:
            data["awaiting_next"] = True
            await cb.message.answer("Переходим к следующему фрагменту?", reply_markup=next_fragment_kb)
        await cb.answer()
        return

    display_text = f"{data['word_order_header']}\n\n**Твоя фраза:** {data['current_assembled']}"
    kb = get_words_keyboard([data["words_list"][i] for i in data["shuffled_indices"]], data["selected_indices"])
    
    try:
        await cb.message.edit_text(display_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass
    await cb.answer()

@router.callback_query(F.data == "word_reset")
async def cb_word_reset(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in current_question:
        return await cb.answer()
    
    data = current_question[user_id]
    data["selected_indices"] = []
    data["current_assembled"] = ""
    
    display_text = f"{data['word_order_header']}\n\n**Твоя фраза:** (пока пусто)"
    kb = get_words_keyboard([data["words_list"][i] for i in data["shuffled_indices"]], data["selected_indices"])
    
    try:
        await cb.message.edit_text(display_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass
    await cb.answer("Выбор сброшен 🔄")

@router.callback_query(F.data == "word_undo")
async def cb_word_undo(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in current_question:
        return await cb.answer()

    data = current_question[user_id]
    if not data.get("selected_indices"):
        return await cb.answer("Пока нечего убирать")

    data["selected_indices"].pop()
    current_words = [data["words_list"][data["shuffled_indices"][i]] for i in data["selected_indices"]]
    data["current_assembled"] = " ".join(current_words)

    phrase = data["current_assembled"] if data["current_assembled"] else "(пока пусто)"
    display_text = f"{data['word_order_header']}\n\n**Твоя фраза:** {phrase}"
    kb = get_words_keyboard([data["words_list"][i] for i in data["shuffled_indices"]], data["selected_indices"])

    try:
        await cb.message.edit_text(display_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass
    await cb.answer("Убрано последнее слово")

async def check_answer(message: Message):
    user_id = message.from_user.id
    if user_id not in current_question or any(current_question[user_id].get(k) for k in ["awaiting_next", "awaiting_continue"]):
        return
    
    data = current_question[user_id]
    song = get_song_by_id(data["song_id"])
    fragment = song["fragments"][data["fragment_index"]]

    # ЗАЩИТА: Если это режим сборки слов, текстовые сообщения тут обрабатывать не нужно!
    if fragment.get("type") == "word_order":
        return

    if message.text.lower().strip() == fragment["answer"].lower().strip():
        score = add_score(user_id, 10)
        trans = fragment.get("translation_ru", "")

        if data["fragment_index"] >= len(song["fragments"]) - 1:
            del current_question[user_id]
            await message.answer(f"✅ Correct! (Total: {score} ⭐)\n\nTranslation: {trans}\n\n🔥 Song Finished!", reply_markup=main_kb)
            return await show_songs_menu(message, user_id)

        if data["song_id"] == "the_beatles_yesterday" and data["fragment_index"] == 4:
            data["awaiting_continue"] = True
            await message.answer(f"✅ Correct! (Total: {score} ⭐)\n\nTranslation: {trans}\n\nPart done! Continue?", reply_markup=pause_choice_kb)
        else:
            data["awaiting_next"] = True
            await message.answer(f"✅ Correct! (Total: {score} ⭐)\n\nTranslation: {trans}", reply_markup=next_fragment_kb)
    else:
        await message.answer(f"❌ Not quite. Correct word: {fragment['answer']}")

async def next_fragment(message: Message):
    uid = message.from_user.id
    if uid in current_question and current_question[uid].get("awaiting_next"):
        current_question[uid].update({"fragment_index": current_question[uid]["fragment_index"] + 1, "awaiting_next": False})
        await send_fragment(message, uid)

async def continue_song(message: Message):
    uid = message.from_user.id
    if uid in current_question and current_question[uid].get("awaiting_continue"):
        current_question[uid].update({"fragment_index": current_question[uid]["fragment_index"] + 1, "awaiting_continue": False})
        await send_fragment(message, uid)

async def cmd_start(message: Message):
    await message.answer("Welcome!", reply_markup=main_kb)
    await show_songs_menu(message, message.from_user.id)

async def show_songs_menu(message: Message, user_id: int | None = None):
    # ИСПРАВЛЕНО: раньше здесь всегда бралось message.from_user.id,
    # а если message приходил из callback-контекста бота (cb.message),
    # это был ID бота, а не игрока — из-за чего счёт всегда показывался как 0.
    # Теперь ID пользователя можно передать явно.
    uid = user_id if user_id is not None else message.from_user.id
    score = get_user_score(uid)
    song_rows = []
    for s in SONGS:
        if "external_url" in s:
            song_rows.append([InlineKeyboardButton(text=s["title"], url=s["external_url"])])
        else:
            song_rows.append([InlineKeyboardButton(text=s["title"], callback_data=f"song:{s['id']}")])
    kb = InlineKeyboardMarkup(
        inline_keyboard=song_rows + [[InlineKeyboardButton(text="Reset Score 🔄", callback_data="reset")]]
    )
    await message.answer(f"Your Total Score: {score} ⭐\nChoose a song:", reply_markup=kb)

async def show_fragments_menu(message: Message, song_id: str):
    song = get_song_by_id(song_id)
    if not song:
        return
    btns = [
        [InlineKeyboardButton(text=str(i + 1), callback_data=f"sel_f:{song_id}:{i}") for i in range(j, min(j + 4, len(song["fragments"])))]
        for j in range(0, len(song["fragments"]), 4)
    ]
    await message.answer(f"Choose a fragment for {song['title']}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("song:"))
async def cb_song(cb: CallbackQuery):
    await cb.answer()
    song_id = cb.data.split(":")[1]
    song = get_song_by_id(song_id)
    intro_id = song.get("intro_video_note") if song else None
    if intro_id:
        await cb.message.answer("🎧 Шаг 1: просто послушай кружочек — без заданий.")
        try:
            await cb.message.answer_video_note(video_note=intro_id)
        except Exception as e:
            await cb.message.answer(f"⚠️ Ошибка отправки кружочка:\n{e}")
    await show_fragments_menu(cb.message, song_id)

@router.message(F.video | F.video_note | F.document)
async def on_video_file_id(message: Message):
    if message.video_note:
        file_id = message.video_note.file_id
        kind = "video_note"
    elif message.video:
        file_id = message.video.file_id
        kind = "video"
    else:
        file_id = message.document.file_id
        kind = "document"
    await message.answer(f"{kind}:\n{file_id}")

@router.callback_query(F.data.startswith("sel_f:"))
async def cb_frag(cb: CallbackQuery):
    _, sid, fidx = cb.data.split(":")
    current_question[cb.from_user.id] = {"song_id": sid, "fragment_index": int(fidx)}
    await cb.answer()
    await send_fragment(cb.message, cb.from_user.id)

@router.callback_query(F.data == "reset")
async def cb_reset(cb: CallbackQuery):
    add_score(cb.from_user.id, -get_user_score(cb.from_user.id))
    await cb.answer("Reset!", show_alert=True)
    # ИСПРАВЛЕНО: передаём cb.from_user.id явно (см. show_songs_menu)
    await show_songs_menu(cb.message, cb.from_user.id)

async def main():
    init_db()
    bot = Bot(token=API_TOKEN, session=AiohttpSession())

    router.message.register(cmd_start, CommandStart())
    router.message.register(on_video_file_id, F.video | F.video_note | F.document)
    router.message.register(next_fragment, F.text == "Next")
    router.message.register(continue_song, F.text == "Continue this song")
    router.message.register(show_songs_menu, F.text.casefold() == "play")
    router.message.register(lambda m: m.answer(f"Score: {get_user_score(m.from_user.id)} ⭐"), F.text == "My score")

    # УДАЛЕНО: здесь раньше стоял рекурсивный вызов asyncio.run(main()),
    # который падал с RuntimeError ("cannot be called from a running event loop")
    # и обрывал регистрацию всех хендлеров ниже (check_answer, cb_word_click,
    # cb_word_reset никогда не регистрировались).

    # ПОСЛЕДНИЙ ХЕНДЛЕР ДЛЯ ТЕКСТА
    router.message.register(check_answer, F.text)

    router.callback_query.register(cb_word_click, F.data.startswith("word:"))
    router.callback_query.register(cb_word_reset, F.data == "word_reset")
    router.callback_query.register(cb_word_undo, F.data == "word_undo")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
