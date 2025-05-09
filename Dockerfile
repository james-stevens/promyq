# (c) Copyright 2024, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible, contact me for more information

FROM alpine:3.18

RUN apk update
RUN apk upgrade

RUN apk add python3 yq jq py-pip py3-requests py3-passlib
RUN pip install yahooquery curl_cffi
RUN pip install yahooquery --upgrade

RUN apk add py3-flask py3-gunicorn py3-yaml

RUN apk add nginx

RUN rm -rf /run/
RUN ln -s /dev/shm /run
RUN rmdir /var/lib/nginx/tmp /var/log/nginx
RUN ln -s /dev/shm /var/lib/nginx/tmp
RUN ln -s /dev/shm /var/log/nginx

RUN apk add prometheus grafana

RUN addgroup -S promyq
RUN adduser -S -G promyq promyq

COPY nginx.conf /etc/nginx/

RUN rm -rf /usr/share/grafana/data /usr/share/grafana/plugins
RUN ln -s /opt/data/grafana/data /usr/share/grafana/data
RUN ln -s /opt/data/grafana/plugins /usr/share/grafana/plugins

COPY conf /usr/share/grafana/conf/

COPY cron.root /var/spool/cron/crontabs/root

COPY etc /usr/local/etc/
COPY bin /usr/local/bin/

COPY python /usr/local/python/
RUN python3 -m compileall /opt/pyrar/python/

COPY inittab /etc/inittab
COPY htdocs /opt/htdocs/

COPY version /etc/
CMD [ "/sbin/init" ]
