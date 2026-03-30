FROM    python:3.13-slim

ENV     PYTHONUNBUFFERED=1
ENV     PYTHONDONTWRITEBYTECODE=1
ENV     DOCKER_HOST=tcp://host.docker.internal:2375

WORKDIR /app

RUN     apt-get update && apt-get install git docker-cli -y

COPY    ["requirements.txt", "."]

RUN     pip install --no-cache-dir -r requirements.txt && rm requirements.txt

COPY    ["src", "."]

RUN     useradd -m nonroot
USER    nonroot

CMD     ["python", "main.py"]
