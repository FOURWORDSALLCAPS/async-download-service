# syntax=docker/dockerfile:1

FROM python:3.9.18-alpine

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip

RUN pip3 install aiofiles aiohttp

EXPOSE 8080

CMD python3 server.py