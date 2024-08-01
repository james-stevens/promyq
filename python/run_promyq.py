#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import flask
import syslog
import yaml
import yahooquery

application = flask.Flask("PromYQ")


class PromYQ:

    def __init__(self):
        self.filename = "/usr/local/etc/promyq.yaml"
        self.trades = None
        self.tickers = None
        self.prices = None
        self.home_currency = None
        self.decimal_places = None

    def load_file(self):
        with open("/usr/local/etc/promyq.yaml") as fd:
            self.trades = yaml.load(fd.read(), Loader=yaml.FullLoader)

        self.home_currency = self.trades[
            "home_currency"] if "home_currency" in self.trades else "USD"
        self.decimal_places = self.trades[
            "places"] if "places" in self.trades else 2

    def get_prices(self):
        self.load_file()
        self.get_all_tickers()

        self.prices = None
        try:
            self.prices = yahooquery.Ticker(self.tickers).price
            return self.prices
        except Exception as exc:
            syslog.syslog(f"ERROR: {exc}")
            return None
        return None

    def get_all_tickers(self):
        self.tickers = None
        all_tickers = {}
        for acct in self.trades:
            if "stocks" in self.trades[acct]:
                for this_trade in self.trades[acct]["stocks"]:
                    if "ticker" in this_trade:
                        all_tickers[this_trade["ticker"]] = True
        self.tickers = list(all_tickers)


promyq = PromYQ()


def trade_metrics(retlist, acct, this_trade):
    if "ticker" not in this_trade:
        return

    this_ticker = this_trade["ticker"]
    if this_ticker not in promyq.prices:
        return

    this_price = promyq.prices[this_ticker]
    this_acct = promyq.trades[acct]
    acct_name = this_acct['name'] if "name" in this_acct else acct

    if "regularMarketPrice" not in this_price:
        syslog.syslog(f"ERROR: regularMarketPrice not in - {this_price}")
        return

    current_value = this_price["regularMarketPrice"] * this_trade["quantity"]

    infill_dict = {
        "account": acct_name,
        "ticker": this_ticker,
        "when": this_trade['date_bought']
    }
    if "tags" in this_acct:
        infill_dict.update(this_acct["tags"])
    if "tags" in this_trade:
        infill_dict.update(this_trade["tags"])
    if "tags" in promyq.trades and this_ticker in promyq.trades["tags"]:
        infill_dict.update(promyq.trades["tags"][this_ticker])

    infill = "{" + ",".join(
        [f"{idx}:\"{val}\"" for idx, val in infill_dict.items()]) + "} "

    retlist.append(f"trade_market_open{infill}" +
                   ("1" if this_price['marketState'] == "REGULAR" else "0"))
    retlist.append(f"trade_current_value{infill}" +
                   format(current_value, f".{promyq.decimal_places}f"))
    retlist.append(f"trade_current_profit{infill}" +
                   format(current_value - this_trade["total_cost"],
                          f".{promyq.decimal_places}f"))


@application.route('/metrics', methods=['GET'])
def get_metrics():
    if promyq.get_prices() is None or promyq.prices is None:
        return flask.make_response("ERROR: prices array is empty",503)

    help_list = [
        f"# HELP trade_current_value Trade current value in {promyq.home_currency}",
        "# TYPE trade_current_value gauge",
        f"# HELP trade_current_profit Trade current profit in {promyq.home_currency}",
        "# TYPE trade_current_profit gauge",
        "# HELP trade_market_open Is the market for this trade open",
        "# TYPE trade_market_open gauge"
    ]

    retlist = []

    for acct in promyq.trades:
        this_acct = promyq.trades[acct]
        if "stocks" in this_acct:
            for this_trade in this_acct["stocks"]:
                trade_metrics(retlist, acct, this_trade)

    if len(retlist) > 0:
        return flask.make_response("\n".join(help_list + retlist) + "\n", 200)
    else:
        print(">>>>",promyq.prices)
        return flask.make_response("ERROR: Failed to get prices",503)


@application.route('/promyq/v1.0/hello', methods=['GET'])
def get_hello():
    resp = flask.make_response(flask.jsonify({"hello": "world"}), 200)
    return resp


def main():
    application.run()


if __name__ == "__main__":
    syslog.syslog("RUNNING WEB/UI")
    main()
