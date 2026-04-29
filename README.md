# Song Guess Telegram Bot (aiogram 3)

Telegram bot game: guess the missing word in song lyrics.

## Features
- 3 songs included by default:
  - Yesterday - The Beatles
  - Flowers - Miley Cyrus
  - Shape of You - Ed Sheeran
- +10 points for each correct answer
- Scores stored in SQLite database (`scores.db`)
- At 50+ points, bot sends a congratulations message and offers a trial English lesson

## Setup
1. Open terminal in this folder:
   - `c:\Users\user\Documents\song_bot`
2. (Optional) Create and activate virtual environment:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Open `bot.py` and set your token in:
   - `API_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"`

## Run
- `python bot.py`

## Notes
- SQLite uses Python built-in `sqlite3`, no extra package needed.
