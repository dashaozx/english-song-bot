import asyncio
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

SONGS = [
    {
        "id": "dragons_bones",
        "title": "Imagine Dragons - Bones 🦴",
        "fragments": [
            {"file": "dragons_bones.mp4", "start": 4, "end": 8, "type": "word_order", "text": "Gimme gimme gimme some time to think\nI'm in the bathroom looking at me", "translation_ru": "Дай мне немного времени подумать, я в ванной смотрю на себя."},
            {"file": "dragons_bones.mp4", "start": 8, "end": 12, "type": "word_order", "text": "Face in the mirror is all I need", "translation_ru": "Лицо в зеркале — это всё, что мне нужно."},
            {"file": "dragons_bones.mp4", "start": 13, "end": 19, "type": "word_order", "text": "Wait until the reaper takes my life\nNever gonna get me out alive\nI will live a thousand million lives", "translation_ru": "Жду, пока жнец заберет мою жизнь. Меня никогда не взять живым, я проживу тысячу миллионов жизней."},
            {"file": "dragons_bones.mp4", "start": 20, "end": 29, "type": "word_order", "text": "My patience is waning\nIs this entertaining\nOur patience is waning\nIs this entertaining", "translation_ru": "Мое терпение на исходе, разве это забавно? Наше терпение на исходе, разве это развлекает?"},
            {"file": "dragons_bones.mp4", "start": 30, "end": 46, "type": "word_order", "text": "Cause there's magic in my bones\nI got this feeling in my soul\nGo ahead and throw your stones", "translation_ru": "Ведь в моих костях магия, это чувство в моей душе, давайте, бросайте свои камни."},
            {"file": "dragons_bones.mp4", "start": 46, "end": 53, "type": "word_order", "text": "Playing with a stick of dynamite\nThere was never gray in black and white\nThere was never wrong til there was right", "translation_ru": "Играю с динамитной шашкой, в черно-белом никогда не было серого, не было неправильного, пока не появилось правильное."},
            {"file": "dragons_bones.mp4", "start": 53, "end": 63, "type": "word_order", "text": "Feeling like a boulder hurtling\nSeeing all the vultures circling\nBurning in the flames I'm working in\nTurning in a bed that's darkening", "translation_ru": "Чувствую себя несущимся валуном, видя, как кружат стервятники. Сгорая в пламени, в котором работаю, ворочаясь в темнеющей постели."},
            {"file": "dragons_bones.mp4", "start": 63, "end": 71, "type": "word_order", "text": "My patience is waning\nIs this entertaining\nOur patience is waning\nIs this entertaining", "translation_ru": "Мое терпение на исходе, разве это забавно? Наше терпение на исходе, разве это развлекает?"},
            {"file": "dragons_bones.mp4", "start": 71, "end": 79, "type": "word_order", "text": "I got this feeling yeah you know\nWhere I'm losing all control\nCause there's magic in my bones", "translation_ru": "У меня это чувство, да, ты знаешь, я теряю контроль, ведь в моих костях магия."},
            {"file": "dragons_bones.mp4", "start": 79, "end": 88, "type": "word_order", "text": "I got this feeling in my soul\nGo ahead and throw your stones\nCause there's magic in my bones", "translation_ru": "Это чувство в моей душе, давайте, бросайте свои камни, ведь в моих костях магия."},
            {"file": "dragons_bones.mp4", "start": 96, "end": 104, "type": "word_order", "text": "Look in the mirror of my mind\nTurning the pages of my life\nWalking the path so many paced a million times", "translation_ru": "Посмотри в зеркало моего разума, переворачивая страницы моей жизни, шагая по тропе, по которой многие ходили миллионы раз."},
            {"file": "dragons_bones.mp4", "start": 105, "end": 112, "type": "word_order", "text": "Drown out the voices in the air\nLeaving the ones that never cared\nPicking the pieces up and building to the sky", "translation_ru": "Заглуши голоса в воздухе, оставив тех, кому было плевать, собирая осколки и строя до небес."},
            {"file": "dragons_bones.mp4", "start": 113, "end": 122, "type": "word_order", "text": "My patience is waning\nIs this entertaining\nMy patience is waning\nIs this entertaining", "translation_ru": "Мое терпение на исходе, разве это интересно? Мое терпение угасает, разве это развлекает?"}
        ]
    },
    {
        "id": "the_beatles_yesterday",
        "title": "Yesterday - The Beatles",
        "fragments": [
            {"file": "y_0.mp4", "text": "Yesterday, all my troubles seemed so far ___", "answer": "away", "translation_ru": "Вчера все мои беды казались такими далекими."},
            {"file": "y_1.mp4", "text": "Now it looks as though they're here to ___", "answer": "stay", "translation_ru": "Теперь кажется, что они здесь надолго."},
            {"file": "y_2.mp4", "text": "Oh, I believe in yesterday.\n___", "answer": "Suddenly", "translation_ru": "О, я верю во вчерашний день."},
            {"file": "y_3.mp4", "text": "I'm not half the ___ I used to be", "answer": "man", "translation_ru": "Я уже и наполовину не тот человек."},
            {"file": "y_4.mp4", "text": "There's a ___ hanging over me", "answer": "shadow", "translation_ru": "Надо мной нависла тень."},
            {"file": "y_5.mp4", "text": "Oh, yesterday came ___", "answer": "suddenly", "translation_ru": "О, вчера наступило внезапно."},
            {"file": "y_6.mp4", "text": "Why she had to ___ I don't know, she wouldn't say", "answer": "go", "translation_ru": "Почему ей пришлось уйти?"},
            {"file": "y_7.mp4", "text": "I said something wrong,\nNow I ___ for yesterday", "answer": "long", "translation_ru": "Теперь я тоскую по вчерашнему дню."},
            {"file": "y_8.mp4", "text": "Yesterday, love was such an ___ game to play", "answer": "easy", "translation_ru": "Вчера любовь была простой игрой."},
            {"file": "y_9.mp4", "text": "Now I need a place to hide away.\nOh, I ___ in yesterday", "answer": "believe", "translation_ru": "О, я верю во вчерашний день."}
        ]
    },
    {
        "id": "miley_flowers",
        "title": "Flowers - Miley Cyrus",
        "fragments": [
            {"file": "fl_0.mp4", "text": "We were good, we were gold\nKind of dream that can't be ___", "answer": "sold", "translation_ru": "Мечта, которую не продать."},
            {"file": "fl_1.mp4", "text": "We were right 'til we weren't\nBuilt a ___ and watched it burn", "answer": "home", "translation_ru": "Построили дом и смотрели, как он горит."},
            {"file": "fl_2.mp4", "text": "I didn't wanna leave you, I didn't wanna ___\nStarted to cry, but then remembered I", "answer": "lie", "translation_ru": "Я не хотела уходить, я не хотела лгать."},
            {"file": "fl_3.mp4", "text": "I can buy myself ___\nWrite my name in the sand", "answer": "flowers", "translation_ru": "Я могу сама купить себе цветы."},
            {"file": "fl_4.mp4", "text": "Talk to myself for ___\nSay things you don't understand", "answer": "hours", "translation_ru": "Разговаривать с собой часами."},
            {"file": "fl_5.mp4", "text": "I can take myself ___\nAnd I can hold my own hand", "answer": "dancing", "translation_ru": "Я могу сама пойти танцевать."},
            {"file": "fl_6.mp4", "text": "Yeah, I can ___ me better\nThan you can", "answer": "love", "translation_ru": "Я могу любить себя лучше, чем ты."},
            {"file": "fl_7.mp4", "text": "Paint my nails cherry ___\nMatch the roses that you left", "answer": "red", "translation_ru": "Крашу ногти в вишнево-красный."},
            {"file": "fl_8.mp4", "text": "No remorse, no ___\nI forgive every word you said", "answer": "regret", "translation_ru": "Никаких сожалений."},
            {"file": "fl_9.mp4", "text": "I didn't wanna leave you, baby, I didn't wanna ___\nStarted to cry, but then remembered I", "answer": "fight", "translation_ru": "Не хотела ругаться."},
            {"file": "fl_10.mp4", "text": "I can buy myself flowers\nWrite my ___ in the sand", "answer": "name", "translation_ru": "Написать свое имя на песке."},
            {"file": "fl_11.mp4", "text": "Talk to myself for ___\nSay things you don't understand", "answer": "hours", "translation_ru": "Разговаривать с собой часами."},
            {"file": "fl_12.mp4", "text": "I can take myself dancing\nAnd I can hold my ___ hand", "answer": "own", "translation_ru": "И могу держать свою собственную руку."}
        ]
    },
    {
        "id": "ed_sheeran_shape",
        "title": "Shape of You - Ed Sheeran",
        "fragments": [
            {"file": "sh_0.mp4", "text": "The club isn't the best place to find a ___\nSo the bar is where I go", "answer": "lover", "translation_ru": "Клуб — не лучшее место для поиска любви."},
            {"file": "sh_1.mp4", "text": "Me and my friends at the table doing ___\nDrinking fast and then we talk slow", "answer": "shots", "translation_ru": "Мы с друзьями пьем шоты."},
            {"file": "sh_2.mp4", "text": "And you come over and start up a conversation with just me\nAnd trust me I'll give it a ___ now", "answer": "chance", "translation_ru": "Поверь, я дам этому шанс."},
            {"file": "sh_3.mp4", "text": "Stop, put the man on the jukebox, and then we start to ___\nAnd now I'm singing like", "answer": "dance", "translation_ru": "Мы начнем танцевать."},
            {"file": "sh_4.mp4", "text": "Girl, you know I want your ___\nYour love was handmade for somebody like me", "answer": "love", "translation_ru": "Девочка, ты знаешь, я хочу твоей любви."},
            {"file": "sh_5.mp4", "text": "Come on now, follow my ___\nI may be crazy, don't mind me", "answer": "lead", "translation_ru": "Давай же, следуй за мной."},
            {"file": "sh_6.mp4", "text": "Say, boy, let's not talk too ___\nGrab on my waist and put that body on me", "answer": "much", "translation_ru": "Парень, давай не будем много болтать."},
            {"file": "sh_7.mp4", "text": "Come on now, follow my lead\nCome, come on now, follow my ___", "answer": "lead", "translation_ru": "Давай же, следуй за мной."},
            {"file": "sh_8.mp4", "text": "I'm in love with the shape of ___\nWe push and pull like a magnet do", "answer": "you", "translation_ru": "Я влюблен в твой силуэт."},
            {"file": "sh_9.mp4", "text": "Although my heart is falling ___\nI'm in love with your body", "answer": "too", "translation_ru": "Хотя мое сердце тоже влюбляется."},
            {"file": "sh_10.mp4", "text": "Last night you were in my ___\nAnd now my bedsheets smell like you", "answer": "room", "translation_ru": "Прошлой ночью ты была в моей комнате."},
            {"file": "sh_11.mp4", "text": "Every day discovering something ___\nI'm in love with your body", "answer": "new", "translation_ru": "Каждый день открываю в тебе что-то новое."},
            {"file": "sh_12.mp4", "text": "One week in we let the story ___\nWe're going out on our first date", "answer": "begin", "translation_ru": "Спустя неделю мы даем истории начаться."},
            {"file": "sh_13.mp4", "text": "You and me are thrifty, so go all you can ___\nFill up your bag and I'll fill up a plate", "answer": "eat", "translation_ru": "Идем туда, где «ешь сколько хочешь»."},
            {"file": "sh_14.mp4", "text": "We talk for hours and hours about the sweet and the ___\nAnd how your family is doing okay", "answer": "sour", "translation_ru": "Мы говорим часами о приятном и горьком."},
            {"file": "sh_15.mp4", "text": "Leave and get in a taxi, then kiss in the back ___\nTell the driver make the radio play", "answer": "seat", "translation_ru": "Садимся в такси, целуемся на заднем сиденье."},
            {"file": "sh_16.mp4", "text": "And I'm singing like\nGirl, you know I want your ___", "answer": "love", "translation_ru": "И я пою: «Девочка, я хочу твоей любви»."},
            {"file": "sh_17.mp4", "text": "Come on now, follow my lead\nI may be crazy, don't mind me\nSay, boy, let's not talk too ___\nGrab on my waist and put that body on me", "answer": "much", "translation_ru": "Парень, давай не будем много болтать."},
            {"file": "sh_18.mp4", "text": "Come on now, follow my lead\nCome, come on now, follow my ___", "answer": "lead", "translation_ru": "Давай же, следуй за мной."}
        ]
    }
]

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
            continue  
        row.append(InlineKeyboardButton(text=word, callback_data=f"word:{idx}"))
        if len(row) == 2:  
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Reset Selection 🔄", callback_data="word_reset")])
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
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s["title"], callback_data=f"song:{s['id']}")] for s in SONGS
        ] + [[InlineKeyboardButton(text="Reset Score 🔄", callback_data="reset")]]
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
    await show_fragments_menu(cb.message, cb.data.split(":")[1])
    await cb.answer()

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

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
