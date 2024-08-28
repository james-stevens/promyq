#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import flask
import syslog

import promyq

application = flask.Flask("PromYQ")


@application.route('/version', methods=['GET'])
def get_version():
    with open("/etc/version") as fd:
        return flask.make_response(fd.readline(), 200)
    return flask.make_response("ERROR: Failed to open version file", 503)


@application.route('/metrics', methods=['GET'])
def get_metrics():
    my_promyq = promyq.PromYQ()
    try:
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
    syslog.syslog("RUNNING WEB/UI")
    main()
