import asyncio
import logging
import os
import re
import sqlite3
import subprocess
import tempfile
import uuid
from typing import Dict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.client.session.aiohttp import AiohttpSession

# --- CONFIG ---
API_TOKEN = os.getenv("BOT_TOKEN", "8562794906:AAHam-UVBOjFJxpr7WCXStTkbZ4s7JfLxqs")
DB_PATH = "scores.db"

logging.basicConfig(level=logging.INFO)

# Создаем диспетчер и роутер здесь, чтобы они были доступны во всем файле
dp = Dispatcher()
router = Router()
dp.include_router(router)

SONGS = [
    {
        "id": "beatles_yesterday",
        "title": "Yesterday - The Beatles",
        "file": "yesterday.mp4",
        "fragments": [
            {"start": 10.0, "end": 17.0, "text": "Yesterday, all my ___ seemed so far away", "answer": "troubles", "translation_ru": "Вчера все мои беды казались такими далекими."},
            {"start": 17.5, "end": 22.0, "text": "Now it ___ as though they're here to stay", "answer": "looks", "translation_ru": "Теперь кажется, будто они остались навсегда."},
            {"start": 22.0, "end": 28.0, "text": "Oh, I ___ in yesterday", "answer": "believe", "translation_ru": "О, я верю во вчерашний день."},
            {"start": 28.0, "end": 36.0, "text": "Suddenly, I'm not half the man I ___ to be", "answer": "used", "translation_ru": "Внезапно я стал совсем не тем человеком, каким был раньше."},
            {"start": 36.5, "end": 40.5, "text": "There's a ___ hanging over me", "answer": "shadow", "translation_ru": "Надо мной нависла тень."},
            {"start": 40.5, "end": 46.5, "text": "Oh, yesterday came ___", "answer": "suddenly", "translation_ru": "О, вчера наступило внезапно."},
            {"start": 46.5, "end": 51.5, "text": "Why she had to ___, I don't know, she wouldn't say", "answer": "go", "translation_ru": "Почему ей пришлось уйти, я не знаю, она не сказала."},
            {"start": 57.0, "end": 65.0, "text": "I said something ___, now I long for yesterday", "answer": "wrong", "translation_ru": "Я сказал что-то не то, и теперь я тоскую по вчерашнему дню."},
            {"start": 65.0, "end": 74.5, "text": "Yesterday, love was such an easy ___ to play", "answer": "game", "translation_ru": "Вчера любовь была такой легкой игрой."},
            {"start": 74.5, "end": 79.5, "text": "Now I need a ___ to hide away", "answer": "place", "translation_ru": "Теперь мне нужно место, чтобы спрятаться."},
            {"start": 79.5, "end": 85.0, "text": "Oh, I believe in ___", "answer": "yesterday", "translation_ru": "О, я верю во вчерашний день."},
            {"start": 85.0, "end": 90.5, "text": "Why she had to go, I don't ___, she wouldn't say", "answer": "know", "translation_ru": "Почему ей пришлось уйти, я не знаю, она не сказала."},
            {"start": 91.0, "end": 99.0, "text": "I ___ something wrong, now I long for yesterday", "answer": "said", "translation_ru": "Я сказал что-то не то, теперь я тоскую по вчерашнему дню."},
            {"start": 100.0, "end": 113.0, "text": "Yesterday, love was such an easy game to ___", "answer": "play", "translation_ru": "Вчера любовь была такой простой игрой."},
            {"start": 113.5, "end": 116.5, "text": "Now I ___ a place to hide away", "answer": "need", "translation_ru": "Теперь мне нужно место, чтобы спрятаться."},
            {"start": 117.0, "end": 125.0, "text": "Oh, I ___ in yesterday", "answer": "believe", "translation_ru": "О, я верю во вчерашний день."}
        ]
    },
    {
        "id": "miley_flowers",
        "title": "Flowers - Miley Cyrus",
        "file": "flowers.mp4",
        "fragments": [
            {"start": 7.0, "end": 11.5, "text": "We were good, we were gold\nKind of dream that can't be ___", "answer": "sold", "translation_ru": "Мы были хороши, мы были золотом. Мечта, которую нельзя продать."},
            {"start": 12.0, "end": 19.5, "text": "We were right 'til we weren't\nBuilt a ___ and watched it burn", "answer": "home", "translation_ru": "Мы были правы, пока не ошиблись. Построили дом и смотрели, как он горит."},
            {"start": 23.0, "end": 27.5, "text": "I didn't wanna leave you, I didn't wanna ___\nStarted to cry, but then remembered I", "answer": "lie", "translation_ru": "Я не хотела уходить, я не хотела лгать. Начала плакать, но потом вспомнила..."},
            {"start": 30.0, "end": 35.5, "text": "I can buy myself ___\nWrite my name in the sand", "answer": "flowers", "translation_ru": "Я могу сама купить себе цветы. Написать своё имя на песке."},
            {"start": 36.0, "end": 43.5, "text": "Talk to myself for ___\nSay things you don't understand", "answer": "hours", "translation_ru": "Разговаривать с собой часами. Говорить вещи, которые ты не понимаешь."},
            {"start": 44.0, "end": 51.5, "text": "I can take myself ___\nAnd I can hold my own hand", "answer": "dancing", "translation_ru": "Я могу сама пойти танцевать. И я могу сама держать себя за руку."},
            {"start": 52.0, "end": 62.0, "text": "Yeah, I can ___ me better\nThan you can", "answer": "love", "translation_ru": "Да, я могу любить себя лучше, чем ты."},
            {"start": 70.0, "end": 74.5, "text": "Paint my nails cherry ___\nMatch the roses that you left", "answer": "red", "translation_ru": "Крашу ногти в вишнево-красный. Под цвет роз, которые ты оставил."},
            {"start": 75.0, "end": 82.5, "text": "No remorse, no ___\nI forgive every word you said", "answer": "regret", "translation_ru": "Ни раскаяния, ни сожаления. Я прощаю каждое твое слово."},
            {"start": 84.0, "end": 90.0, "text": "I didn't wanna leave you, baby, I didn't wanna ___\nStarted to cry, but then remembered I", "answer": "fight", "translation_ru": "Я не хотела уходить, малыш, я не хотела ссориться. Начала плакать, но потом вспомнила..."},
            {"start": 91.0, "end": 100.5, "text": "I can buy myself flowers\nWrite my ___ in the sand", "answer": "name", "translation_ru": "Я могу сама купить себе цветы. Написать своё имя на песке."},
            {"start": 101.0, "end": 108.0, "text": "Talk to myself for ___\nSay things you don't understand", "answer": "hours", "translation_ru": "Разговаривать с собой часами. Говорить вещи, которые ты не понимаешь."},
            {"start": 110.5, "end": 117.0, "text": "I can take myself dancing\nAnd I can hold my ___ hand", "answer": "own", "translation_ru": "Я могу сама пойти танцевать. И я могу сама держать свою руку."},
            {"start": 117.5, "end": 123.0, "text": "Yeah, I can ___ me better\nThan you can", "answer": "love", "translation_ru": "Да, я могу любить себя лучше, чем ты можешь."}
        ], # Запятая после списка фрагментов
    },
    {
        "id": "ed_shape_of_you",
        "title": "Shape of You - Ed Sheeran",
        "file": "shape_of_you.mp4",
        "fragments": [
            {"start": 13.0, "end": 20.0, "text": "The club isn't the best place to find a lover, so the ___ is where I go", "answer": "bar", "translation_ru": "Клуб — не лучшее место, поэтому бар — это то место, куда я иду."},
            {"start": 20.0, "end": 25.0, "text": "Me and my friends at the table doing ___", "answer": "shots", "translation_ru": "Я и мои друзья за столом пьем шоты."},
            {"start": 56.0, "end": 62.0, "text": "I'm in love with the ___ of you", "answer": "shape", "translation_ru": "Я влюблен в твои очертания."},
            {"start": 76.0, "end": 81.0, "text": "Oh I, oh I, oh I, oh I \nI'm in ___ with your body", "answer": "love", "translation_ru": "Я влюблен в твое тело."},
        ],
    },
]

# --- KEYBOARDS ---
main_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Play")], [KeyboardButton(text="My score")]], resize_keyboard=True)
next_fragment_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Next")], [KeyboardButton(text="Play"), KeyboardButton(text="My score")]], resize_keyboard=True)
pause_choice_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Continue this song")], [KeyboardButton(text="Choose another song")]], resize_keyboard=True)

current_question: Dict[int, Dict[str, object]] = {}

# --- DB LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, score INTEGER NOT NULL DEFAULT 0)")
    conn.commit()
    conn.close()

def get_user_score(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO users (user_id, score) VALUES (?, 0)", (user_id,))
        conn.commit(); score = 0
    else: score = int(row[0])
    conn.close(); return score

def add_score(user_id: int, points: int) -> int:
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (points, user_id))
    conn.commit(); conn.close()
    return get_user_score(user_id)

# --- UTILS ---
def get_song_by_id(song_id: str) -> dict | None:
    return next((s for s in SONGS if s["id"] == song_id), None)

def escape_markdown(text: str) -> str:
    for ch in ("`", "*", "_", "[", "]", "(", ")"): text = text.replace(ch, f"\\{ch}")
    return text

def format_translation_markdown(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

# --- CORE LOGIC ---
async def send_fragment(message: Message, user_id: int):
    data = current_question.get(user_id)
    if not data: return await show_songs_menu(message)

    song = get_song_by_id(data["song_id"])
    idx = data["fragment_index"]
    
    if idx >= len(song["fragments"]):
        if user_id in current_question: del current_question[user_id]
        await message.answer("🎉 You've finished this song!", reply_markup=main_kb)
        return await show_songs_menu(message)

    fragment = song["fragments"][idx]
    await message.answer(f"Song: {song['title']}\nFragment {idx + 1}/{len(song['fragments'])}\n\nFill in the missing word:\n{escape_markdown(fragment['text'])}", parse_mode="Markdown")
    
    source_path = os.path.join("audio", song["file"])
    video_note_path = build_video_note_clip(source_path, float(fragment["start"]), float(fragment["end"]))
    if video_note_path:
        await message.bot.send_video_note(chat_id=message.chat.id, video_note=FSInputFile(video_note_path))
        if os.path.exists(video_note_path): os.remove(video_note_path)

async def check_answer(message: Message):
    user_id = message.from_user.id
    if user_id not in current_question: return
    
    data = current_question[user_id]
    if data.get("awaiting_next") or data.get("awaiting_continue"): return

    song = get_song_by_id(data["song_id"])
    idx = data["fragment_index"]
    fragment = song["fragments"][idx]
    
    if message.text.lower().strip() == fragment["answer"].lower().strip():
        score = add_score(user_id, 1)
        trans = format_translation_markdown(fragment["translation_ru"])
        
        if idx >= len(song["fragments"]) - 1:
            del current_question[user_id]
            await message.answer(f"Correct! (Total: {score} ⭐)\n\nTranslation: {trans}\n\n🔥 Song Finished!", reply_markup=main_kb, parse_mode="Markdown")
            return await show_songs_menu(message)

        if (data["song_id"] == "beatles_yesterday" and idx == 4):
            data["awaiting_continue"] = True
            await message.answer(f"Correct! (Total: {score} ⭐)\n\nTranslation: {trans}\n\nFirst part done! Continue?", reply_markup=pause_choice_kb, parse_mode="Markdown")
        else:
            data["awaiting_next"] = True
            await message.answer(f"Correct! (Total: {score} ⭐)\n\nTranslation: {trans}", reply_markup=next_fragment_kb, parse_mode="Markdown")
    else:
        await message.answer(f"Not quite. Correct word: *{fragment['answer']}*", parse_mode="Markdown")

async def next_fragment(message: Message):
    user_id = message.from_user.id
    if user_id in current_question and current_question[user_id].get("awaiting_next"):
        current_question[user_id]["fragment_index"] += 1
        current_question[user_id]["awaiting_next"] = False
        await send_fragment(message, user_id)

async def continue_song(message: Message):
    user_id = message.from_user.id
    if user_id in current_question and current_question[user_id].get("awaiting_continue"):
        current_question[user_id]["fragment_index"] += 1
        current_question[user_id]["awaiting_continue"] = False
        await send_fragment(message, user_id)

def build_video_note_clip(source_path, start_time, end_time):
    if not os.path.exists(source_path): return None
    out = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.mp4")
    cmd = ["ffmpeg", "-y", "-ss", str(start_time), "-i", source_path, "-t", str(end_time-start_time), 
           "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=480:480", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out]
    if subprocess.run(cmd, capture_output=True).returncode == 0: return out
    return None

# --- HANDLERS ---
async def cmd_start(message: Message):
    await message.answer("Welcome to the Song Game!", reply_markup=main_kb)
    await show_songs_menu(message)

async def show_songs_menu(message: Message):
    score = get_user_score(message.from_user.id)
    buttons = [[InlineKeyboardButton(text=s["title"], callback_data=f"song:{s['id']}")] for s in SONGS]
    buttons.append([InlineKeyboardButton(text="Reset Score 🔄", callback_data="reset")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(f"Your Total Score: {score} ⭐\nChoose a song:", reply_markup=kb)

async def show_fragments_menu(message: Message, song_id: str):
    song = next((s for s in SONGS if s["id"] == song_id), None)
    if not song: return
    kb_list = []
    row = []
    for i in range(len(song["fragments"])):
        row.append(InlineKeyboardButton(text=str(i+1), callback_data=f"select_frag:{song_id}:{i}"))
        if len(row) == 4:
            kb_list.append(row)
            row = []
    if row: kb_list.append(row)
    kb = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await message.answer(f"Choose a fragment for {song['title']}:", reply_markup=kb)

# --- CALLBACKS (используем router) ---
@router.callback_query(F.data.startswith("song:"))
async def choose_song_callback(cb: CallbackQuery):
    song_id = cb.data.split(":")[1]
    await cb.answer()
    await show_fragments_menu(cb.message, song_id)

@router.callback_query(F.data.startswith("select_frag:"))
async def select_fragment_callback(cb: CallbackQuery):
    _, song_id, frag_index = cb.data.split(":")
    user_id = cb.from_user.id
    current_question[user_id] = {"song_id": song_id, "fragment_index": int(frag_index)}
    await cb.answer()
    await send_fragment(cb.message, user_id)
@router.callback_query(F.data == "reset")
async def reset_score_callback(cb: CallbackQuery):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET score = 0 WHERE user_id = ?", (cb.from_user.id,))
    conn.commit()
    conn.close()
    await cb.answer("Score reset to 0!", show_alert=True)
    await show_songs_menu(cb.message)
# --- MAIN ---
async def main():
    init_db()
    
    # Создаем сессию и бота
    session = AiohttpSession()
    bot = Bot(token=API_TOKEN, session=session)
    
    # ВАЖНО: используем тот dp, который создали в начале файла, 
    # а не создаем новый!
    
    # Регистрируем все обработчики сообщений
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(next_fragment, F.text == "Next")
    dp.message.register(continue_song, F.text == "Continue this song")
    dp.message.register(show_songs_menu, F.text.casefold() == "play")
    dp.message.register(lambda m: m.answer(f"Your score: {get_user_score(m.from_user.id)} ⭐"), F.text == "My score")
    
    # Этот обработчик должен быть ПОСЛЕДНИМ, так как он ловит любой текст
    dp.message.register(check_answer, F.text)
    
    print("Бот запущен и готов к работе...")
    
    try:
        # Очищаем очередь старых сообщений и запускаем
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
    # Регистрация команд
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(next_fragment, F.text == "Next")
    dp.message.register(continue_song, F.text == "Continue this song")
    dp.message.register(show_songs_menu, F.text.casefold() == "play")
    dp.message.register(lambda m: m.answer(f"Your score: {get_user_score(m.from_user.id)} ⭐"), F.text == "My score")
    dp.message.register(check_answer, F.text)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")