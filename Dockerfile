# Base python
FROM python:3.7

ARG BRANCH="master"

RUN apt-get update && apt-get -y install wget git

RUN mkdir -p /app

WORKDIR /app

RUN git clone -b ${BRANCH} https://github.com/siverpro/CRAPPy.git

WORKDIR /app/CRAPPy

RUN pip install -r requirements.txt

CMD ["python", "-u", "./main.py" ]