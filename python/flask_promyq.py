#! /usr/bin/python3
# (c) Copyright 2019-2024, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import os
import flask

import promyq

application = flask.Flask("PromYQ")

with open("/etc/version") as fd:
    this_version = fd.readline().strip()


@application.route('/version', methods=['GET'])
def get_version():
    return flask.make_response(this_version, 200)


@application.route('/promyq/config', methods=['GET'])
def get_config():
    my_config = {
        "refresh_interval":
        os.environ["PROMYQ_REFRESH_INTERVAL"] if "PROMYQ_REFRESH_INTERVAL" in os.environ else "300s",
        "retention_time": os.environ["PROMYQ_RETENTION_TIME"] if "PROMYQ_RETENTION_TIME" in os.environ else "180d",
        "version": this_version
    }
    return flask.make_response(flask.jsonify(my_config), 200)


@application.route('/promyq/trades', methods=['GET'])
def get_trades():
    try:
        my_promyq = promyq.PromYQ()
        return flask.make_response(my_promyq.current_config(), 200)
    except promyq.PromyqError as e:
        return flask.make_response(f"{str(e)}", 503)


@application.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        my_promyq = promyq.PromYQ()
        prom_metrics = my_promyq.prometheus_metrics()
        return flask.make_response("\n".join(prom_metrics) + "\n", 200)
    except promyq.PromyqError as e:
        return flask.make_response(f"{str(e)}", 503)


@application.route('/', methods=['GET'])
def get_hello():
    resp = flask.make_response(flask.jsonify({"hello": "world"}), 200)
    return resp


def main():
    application.run()


if __name__ == "__main__":
    main()
