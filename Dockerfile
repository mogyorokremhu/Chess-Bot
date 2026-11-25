FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/usr/games:${PATH}"
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY lichess_bot lichess_bot
COPY config.example.yml /app/config.example.yml
# Mount your config at /app/config.yml and pass LICHESS_TOKEN as an env var.
CMD ["python", "-m", "lichess_bot", "-c", "/app/config.yml"]
