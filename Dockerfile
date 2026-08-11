# Bothost: force Python (repo has app/*.js — auto-detect may pick Node)
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

# Persistent volume on Bothost is /app/data
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8080

CMD ["python", "-u", "bot.py"]
