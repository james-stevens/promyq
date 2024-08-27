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
    if not my_promyq.get_prices():
        return flask.make_response("ERROR: get prices failed 503")

    if not my_promyq.all_data_ok():
        return flask.make_response("ERROR: Failed to pass all_data_ok()", 503)

    help_list = my_promyq.get_help_list()

    ticker_list = my_promyq.tickers_list_all()
    if len(ticker_list) <= 0:
        return flask.make_response("ERROR: Failed to get ticker metrics", 503)

    trades_list = my_promyq.trades_list_all()
    if len(trades_list) <= 0:
        return flask.make_response("ERROR: Failed to get trade metrics", 503)

    return flask.make_response("\n".join(help_list + trades_list + ticker_list) + "\n", 200)


@application.route('/', methods=['GET'])
def get_hello():
    resp = flask.make_response(flask.jsonify({"hello": "world"}), 200)
    return resp


def main():
    application.run()


if __name__ == "__main__":
    syslog.syslog("RUNNING WEB/UI")
    main()
