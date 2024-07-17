# (c) Copyright 2024, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible, contact me for more information

FROM alpine:3.18

RUN apk add python3 jq py-pip py3-requests
RUN pip install yahooquery
RUN pip install yahooquery --upgrade

RUN apk add py3-flask py3-gunicorn py3-yaml

COPY python /usr/local/python/
RUN python3 -m compileall /opt/pyrar/python/

RUN apk add nginx

RUN rm -rf /run/
RUN ln -s /dev/shm /run
RUN rmdir /var/lib/nginx/tmp /var/log/nginx
RUN ln -s /dev/shm /var/lib/nginx/tmp
RUN ln -s /dev/shm /var/log/nginx

RUN mkdir -p /opt/htdocs
COPY index.html /opt/htdocs/

COPY nginx.conf /etc/nginx/

RUN apk add prometheus

COPY etc /usr/local/etc/
COPY bin /usr/local/bin/

COPY inittab /etc/inittab
CMD [ "/sbin/init" ]
