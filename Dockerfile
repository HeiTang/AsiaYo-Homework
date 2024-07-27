# Dockerfile for a Flask API
FROM python:3.12
WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["flask", "run"]