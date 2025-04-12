FROM python:3.11-slim

WORKDIR /app

COPY olx-bot.py .

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["python3", "olx-bot.py"]  