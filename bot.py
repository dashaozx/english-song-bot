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
        "id": "the_beatles_yesterday",
        "title": "Yesterday - The Beatles",
        "fragments": [
            {"file": "yesterday.mp4", "text": "(11-18 сек)\nYesterday, all my troubles seemed so far ___", "answer": "away", "translation_ru": "Вчера все мои беды казались такими далекими."},
            {"file": "yesterday.mp4", "text": "(18.5-23 сек)\nNow it looks as though they're here to ___", "answer": "stay", "translation_ru": "Теперь кажется, что они здесь надолго."},
            {"file": "yesterday.mp4", "text": "(23.5-30 сек)\nOh, I believe in yesterday.\n___", "answer": "Suddenly", "translation_ru": "О, я верю во вчерашний день. Внезапно..."},
            {"file": "yesterday.mp4", "text": "(30.5-35 сек)\nI'm not half the ___ I used to be", "answer": "man", "translation_ru": "Я уже и наполовину не тот человек, которым был раньше."},
            {"file": "yesterday.mp4", "text": "(35.5-40 сек)\nThere's a ___ hanging over me", "answer": "shadow", "translation_ru": "Надо мной нависла тень."},
            {"file": "yesterday.mp4", "text": "(40.5-45 сек)\nOh, yesterday came ___", "answer": "suddenly", "translation_ru": "О, вчера наступило внезапно."},
            {"file": "yesterday.mp4", "text": "(45.5-55 сек)\nWhy she had to ___ I don't know, she wouldn't say", "answer": "go", "translation_ru": "Почему ей пришлось уйти? Я не знаю, она не сказала."},
            {"file": "yesterday.mp4", "text": "(55.5-66 сек)\nI said something wrong,\nNow I ___ for yesterday", "answer": "long", "translation_ru": "Я сказал что-то не то, теперь я тоскую по вчерашнему дню."},
            {"file": "yesterday.mp4", "text": "(66.5-75 сек)\nYesterday, love was such an ___ game to play", "answer": "easy", "translation_ru": "Вчера любовь была такой простой игрой."},
            {"file": "yesterday.mp4", "text": "(75.5-84 сек)\nNow I need a place to hide away.\nOh, I ___ in yesterday", "answer": "believe", "translation_ru": "Теперь мне нужно место, чтобы спрятаться. О, я верю во вчерашний день."}
        ]
    }
    {
        "id": "miley_flowers",
        "title": "Flowers - Miley Cyrus",
        "fragments": [
            {"file": "fl_0.mp4", "text": "We were good, we were gold\nKind of dream that can't be ___", "answer": "sold", "translation_ru": "Мы были хороши, мы были золотыми. Мечта, которую не продать."},
            {"file": "fl_1.mp4", "text": "We were right 'til we weren't\nBuilt a ___ and watched it burn", "answer": "home", "translation_ru": "Мы были правы, пока не ошиблись. Построили дом и смотрели, как он горит."},
            {"file": "fl_2.mp4", "text": "I didn't wanna leave you, I didn't wanna ___\nStarted to cry, but then remembered I", "answer": "lie", "translation_ru": "Я не хотела уходить, я не хотела лгать. Начала плакать, но потом вспомнила..."},
            {"file": "fl_3.mp4", "text": "I can buy myself ___\nWrite my name in the sand", "answer": "flowers", "translation_ru": "Я могу сама купить себе цветы. Написать свое имя на песке."},
            {"file": "fl_4.mp4", "text": "Talk to myself for ___\nSay things you don't understand", "answer": "hours", "translation_ru": "Разговаривать с собой часами. Говорить вещи, которые ты не понимаешь."},
            {"file": "fl_5.mp4", "text": "I can take myself ___\nAnd I can hold my own hand", "answer": "dancing", "translation_ru": "Я могу сама пойти танцевать. И я могу держать себя за руку."},
            {"file": "fl_6.mp4", "text": "Yeah, I can ___ me better\nThan you can", "answer": "love", "translation_ru": "Да, я могу любить себя лучше, чем ты."},
            {"file": "fl_7.mp4", "text": "Paint my nails cherry ___\nMatch the roses that you left", "answer": "red", "translation_ru": "Крашу ногти в вишнево-красный под цвет роз, что ты оставил."},
            {"file": "fl_8.mp4", "text": "No remorse, no ___\nI forgive every word you said", "answer": "regret", "translation_ru": "Никакого раскаяния, никаких сожалений. Я прощаю каждое твое слово."},
            {"file": "fl_9.mp4", "text": "I didn't wanna leave you, baby, I didn't wanna ___\nStarted to cry, but then remembered I", "answer": "fight", "translation_ru": "Я не хотела уходить, малыш, не хотела ругаться."},
            {"file": "fl_10.mp4", "text": "I can buy myself flowers\nWrite my ___ in the sand", "answer": "name", "translation_ru": "Я могу сама купить себе цветы. Написать свое имя на песке."},
            {"file": "fl_11.mp4", "text": "Talk to myself for ___\nSay things you don't understand", "answer": "hours", "translation_ru": "Разговаривать с собой часами."},
            {"file": "fl_12.mp4", "text": "I can take myself dancing\nAnd I can hold my ___ hand", "answer": "own", "translation_ru": "Я могу сама пойти танцевать. И могу держать свою собственную руку."}
        ]
    },
    {
    "id": "ed_sheeran_shape",
    "title": "Shape of You - Ed Sheeran",
   "fragments": [
            {"file": "sh_0.mp4", "text": "The club isn't the best place to find a ___\nSo the bar is where I go", "answer": "lover", "translation_ru": "Клуб — не лучшее место для поиска любви."},
            {"file": "sh_1.mp4", "text": "Me and my friends at the table doing ___\nDrinking fast and then we talk slow", "answer": "shots", "translation_ru": "Мы с друзьями пьем шоты."},
            {"file": "sh_2.mp4", "text": "And you come over and start up a conversation with just me\nAnd trust me I'll give it a ___ now", "answer": "chance", "translation_ru": "Подойди и заговори со мной, я дам нам шанс."},
            {"file": "sh_3.mp4", "text": "Stop, put the man on the jukebox, and then we start to ___\nAnd now I'm singing like", "answer": "dance", "translation_ru": "Поставь песню, и мы начнем танцевать."},
            {"file": "sh_4.mp4", "text": "Girl, you know I want your ___\nYour love was handmade for somebody like me", "answer": "love", "translation_ru": "Девочка, ты знаешь, я хочу твоей любви."},
            {"file": "sh_5.mp4", "text": "Come on now, follow my ___\nI may be crazy, don't mind me", "answer": "lead", "translation_ru": "Давай, следуй за мной."},
            {"file": "sh_6.mp4", "text": "Say, boy, let's not talk too ___\nGrab on my waist and put that body on me", "answer": "much", "translation_ru": "Парень, давай не будем много болтать."},
            {"file": "sh_7.mp4", "text": "Come on now, follow my lead\nCome, come on now, follow my ___", "answer": "lead", "translation_ru": "Давай же, следуй за мной."},
            {"file": "sh_8.mp4", "text": "I'm in love with the shape of ___\nWe push and pull like a magnet do", "answer": "you", "translation_ru": "Я влюблен в твой силуэт."},
            {"file": "sh_9.mp4", "text": "Although my heart is falling ___\nI'm in love with your body", "answer": "too", "translation_ru": "Мое сердце тоже влюбляется."},
            {"file": "sh_10.mp4", "text": "Last night you were in my ___\nAnd now my bedsheets smell like you", "answer": "room", "translation_ru": "Прошлой ночью ты была в моей комнате."},
            {"file": "sh_11.mp4", "text": "Every day discovering something ___\nI'm in love with your body", "answer": "new", "translation_ru": "Каждый день открываю в тебе что-то новое."},
            {"file": "sh_12.mp4", "text": "One week in we let the story ___\nWe're going out on our first date", "answer": "begin", "translation_ru": "Спустя неделю мы даем истории начаться."},
            {"file": "sh_13.mp4", "text": "You and me are thrifty, so go all you can ___\nFill up your bag and I’ll fill up a plate", "answer": "eat", "translation_ru": "Идем туда, где «ешь сколько хочешь»."},
            {"file": "sh_14.mp4", "text": "We talk for hours and hours about the sweet and the ___\nAnd how your family is doing okay", "answer": "sour", "translation_ru": "Мы часами болтаем о приятном и горьком."},
            {"file": "sh_15.mp4", "text": "Leave and get in a taxi, then kiss in the back ___\nTell the driver make the radio play", "answer": "seat", "translation_ru": "Садимся в такси, целуемся на заднем сиденье."},
            {"file": "sh_16.mp4", "text": "And I'm singing like\nGirl, you know I want your ___", "answer": "love", "translation_ru": "И я пою: «Девочка, я хочу твоей любви»."},
            {"file": "sh_17.mp4", "text": "Come on now, follow my lead\nI may be crazy, don't mind me\nSay, boy, let's not talk too ___\nGrab on my waist and put that body on me", "answer": "much", "translation_ru": "Давай, следуй за мной. Я могу быть сумасшедшим, не обращай внимания. Парень, давай не будем много болтать."},
            {"file": "sh_18.mp4", "text": "Come on now, follow my lead\nCome, come on now, follow my ___", "answer": "lead", "translation_ru": "Давай же, следуй за мной."}
        ]
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
    if not data: 
        return await show_songs_menu(message)

    song = get_song_by_id(data["song_id"])
    idx = data["fragment_index"]
    
    # Проверка на завершение песни
    if idx >= len(song["fragments"]):
        if user_id in current_question: 
            del current_question[user_id]
        await message.answer("🎉 You've finished this song!", reply_markup=main_kb)
        return await show_songs_menu(message)

    fragment = song["fragments"][idx]
    
    # 1. Отправляем текст вопроса (строго один раз)
    await message.answer(
        f"Song: {song['title']}\nFragment {idx + 1}/{len(song['fragments'])}\n\n"
        f"Fill in the missing word:\n{fragment['text']}"
    )

    # 2. Определяем путь к уже нарезанному файлу
    video_note_path = os.path.join("audio", fragment["file"])
    
    # 3. Отправляем ОДИН кружок
    if os.path.exists(video_note_path):
        await message.bot.send_video_note(
            chat_id=message.chat.id, 
            video_note=FSInputFile(video_note_path)
        )
    else:
        await message.answer(f"⚠️ File not found: {fragment['file']}. Check 'audio' folder.")
async def check_answer(message: Message):
    user_id = message.from_user.id
    if user_id not in current_question:
        return 

    data = current_question[user_id]
    
    # Если бот ждет нажатия кнопки (Next/Continue), игнорируем повторный ввод текста
    if data.get("awaiting_next") or data.get("awaiting_continue"):
        return

    song = get_song_by_id(data["song_id"])
    idx = data["fragment_index"]
    fragment = song["fragments"][idx]
    
    # Сверяем ответ (убираем пробелы и приводим к нижнему регистру)
    user_answer = message.text.lower().strip()
    correct_answer = fragment["answer"].lower().strip()

    if user_answer == correct_answer:
        score = add_score(user_id, 1)
        # Безопасно форматируем перевод
        trans_text = fragment.get("translation_ru", "No translation available")
        trans = format_translation_markdown(trans_text)
        
        # 1. Если это был последний фрагмент песни
        if idx >= len(song["fragments"]) - 1:
            del current_question[user_id]
            await message.answer(
                f"✅ **Correct!** (Total: {score} ⭐)\n\n"
                f"**Translation:** {trans}\n\n"
                f"🔥 **Song Finished!**", 
                reply_markup=main_kb, 
                parse_mode="Markdown"
            )
            return await show_songs_menu(message)

        # 2. Спец-условие для Yesterday (пауза на 4-м фрагменте)
        if data["song_id"] == "beatles_yesterday" and idx == 4:
            data["awaiting_continue"] = True
            await message.answer(
                f"✅ **Correct!** (Total: {score} ⭐)\n\n"
                f"**Translation:** {trans}\n\n"
                f"First part done! Continue?", 
                reply_markup=pause_choice_kb, 
                parse_mode="Markdown"
            )
        
        # 3. Обычный переход к следующему фрагменту
        else:
            data["awaiting_next"] = True
            await message.answer(
                f"✅ **Correct!** (Total: {score} ⭐)\n\n"
                f"**Translation:** {trans}", 
                reply_markup=next_fragment_kb, 
                parse_mode="Markdown"
            )
    else:
        # Если ответ неверный
        await message.answer(
            f"❌ Not quite. Correct word: *{fragment['answer']}*", 
            parse_mode="Markdown"
        )

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
