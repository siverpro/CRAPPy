# Base python
FROM python:3.7 as base

ARG BRANCH="master"

RUN apt-get update && apt-get -y install wget curl git

RUN mkdir -p /app

WORKDIR /app

RUN git clone -b ${BRANCH} https://github.com/siverpro/CRAPPy.git

WORKDIR /app/CRAPPy

COPY main.py /main.py

RUN chmod +x /main.py

ENTRYPOINT ["/main.py"]
