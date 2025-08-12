FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements_site.txt /app/requirements_site.txt
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements_site.txt && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir yt-dlp
COPY . /app
EXPOSE 8000
CMD ["sh","-lc","uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]

