FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY stream_mao.py  /app
EXPOSE 9000
#CMD ["uvicorn", "stream_mao:app", "--host", "0.0.0.0", "--port", "9000"]
CMD ["gunicorn", "stream_mao:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "4", "--timeout", "600", "--keep-alive", "30","--bind", "0.0.0.0:9000"]

