#! /usr/bin/python3
# (c) Copyright 2019-2025, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import os
import flask
import syslog
from passlib.hash import sha256_crypt

import json
import promyq
import log

MAX_TRIES = 5

application = flask.Flask("PromYQ")

with open("/etc/version") as fd:
    this_version = fd.readline().strip()

log_facility = syslog.LOG_LOCAL1

if "PROMYQ_FACILITY" in os.environ and os.environ["PROMYQ_FACILITY"] in log.facility_options:
    log_facility = log.facility_options[os.environ["PROMYQ_FACILITY"]]

syslog.openlog("PromYQ", logoption=syslog.LOG_PID, facility=log_facility)


@application.route('/version', methods=['GET'])
def get_version():
    return flask.make_response(this_version, 200)


@application.route('/promyq/encrypt', methods=['POST'])
def encrypt_password():
    js = flask.request.json
    if js is None or "password" not in js:
        return flask.make_response("'password' field missing", 499)
    return flask.make_response(flask.jsonify({"hash": sha256_crypt.using(rounds=5000).hash(js["password"])}), 200)


@application.route('/promyq/config', methods=['GET'])
def get_config():
    my_config = {"version": this_version}
    return flask.make_response(flask.jsonify(my_config), 200)


@application.route('/promyq/trades', methods=['GET'])
def get_trades():
    try:
        my_promyq = promyq.PromYQ()
        return flask.make_response(json.dumps(my_promyq.current_config(), separators=(',', ':'), default=str), 200)
    except promyq.PromyqError as e:
        return flask.make_response(f"{str(e)}", 503)


@application.route('/metrics', methods=['GET'])
def get_metrics():
    my_promyq = promyq.PromYQ()
    err = None
    for id in range(0, MAX_TRIES):
        try:
            prom_metrics = my_promyq.prometheus_metrics()
            return flask.make_response("\n".join(prom_metrics) + "\n", 200)
        except promyq.PromyqError as e:
            err = str(e)
            syslog.syslog(syslog.LOG_WARNING, f"WARNING: Fetch prices failed, attempt {id} - {err}")
    syslog.syslog(syslog.LOG_ERROR, f"ERROR: Fetching trades failed after {MAX_TRIES} attempts")
    return flask.make_response(f"{err}", 503)


@application.route('/', methods=['GET'])
def get_hello():
    resp = flask.make_response(flask.jsonify({"hello": "world"}), 200)
    return resp


def main():
    application.run()


if __name__ == "__main__":
    main()
