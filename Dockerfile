# (c) Copyright 2024, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible, contact me for more information

FROM alpine:3.18

RUN apk add python3 jq py-pip
RUN pip install yahooquery
RUN pip install yahooquery --upgrade

RUN apk add py3-flask py3-gunicorn
