FROM python:3.10

# Устанавливаем ffmpeg для нарезки видео
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

# Копируем всё содержимое папки в контейнер (включая songs.json)
COPY . .
COPY songs.json .

# Устанавливаем библиотеку для бота
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем бота
CMD ["python", "bot.py"]