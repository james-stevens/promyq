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
        self.rates = None
        self.home_currency = "USD"
        self.decimal_places = 2

    def load_file(self):
        with open("/usr/local/etc/promyq.yaml") as fd:
            self.trades = yaml.load(fd.read(), Loader=yaml.FullLoader)

        if "currency" in self.trades:
            cur = self.trades["currency"]
            if "places" in cur:
                self.decimal_places = cur["places"]
            if "ticker" in cur:
                self.home_currency = cur["ticker"]

    def get_prices(self):
        self.load_file()
        self.get_all_tickers()
        ret = self.get_all_prices()
        self.get_all_currencies()
        print(self.rates)
        return ret

    def get_all_prices(self):
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

    def get_all_currencies(self):
        p_dict = {
            self.prices[p]["currency"]: True
            for p in self.prices if "currency" in self.prices[p]
        }
        currencies = [
            self.home_currency + p.upper() + "=X" for p in p_dict
            if p.upper() != self.home_currency
        ]
        self.rates = None
        try:
            self.rates = yahooquery.Ticker(currencies).price
            return self.rates
        except Exception as exc:
            syslog.syslog(f"ERROR: {exc}")
            return None
        return None


promyq = PromYQ()


def ticker_metrics(retlist, this_ticker):
    if this_ticker not in promyq.prices:
        return

    this_price = promyq.prices[this_ticker]
    if "regularMarketPrice" not in this_price:
        return

    if "currency" in this_price and this_price[
            "currency"] == "GBp" and this_price["regularMarketPrice"] > 5:
        for item in ["regularMarketPrice", "regularMarketChange"]:
            this_price[item] = this_price[item] / 100
        this_price["currency"] = "GBP"

    infill_dict = {"ticker": this_ticker}
    if "longName" in this_price:
        infill_dict["name"] = this_price["longName"]
    if "currency" in this_price:
        infill_dict["currency"] = this_price["currency"]

    # user applied tags
    if "tags" in promyq.trades and this_ticker in promyq.trades["tags"]:
        infill_dict.update(promyq.trades["tags"][this_ticker])

    infill = "{" + ",".join(
        [f"{idx}:\"{val}\"" for idx, val in infill_dict.items()]) + "} "

    if "regularMarketChange" in this_price:
        retlist.append(f"ticker_day_move{infill}" + format(
            this_price["regularMarketChange"], f".{promyq.decimal_places}f"))

    retlist.append(
        f"ticker_price{infill}" +
        format(this_price["regularMarketPrice"], f".{promyq.decimal_places}f"))

    retlist.append(f"ticker_market_open{infill}" +
                   ("1" if this_price['marketState'] == "REGULAR" else "0"))


def trade_metrics(promyq, retlist, acct, this_trade):
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
        "currency": promyq.home_currency,
        "when": this_trade['date_bought']
    }

    # user applied tags
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
        return flask.make_response("ERROR: prices array is empty", 503)

    help_list = [
        f"# HELP trade_current_value Trade current value in {promyq.home_currency}",
        "# TYPE trade_current_value gauge",
        f"# HELP trade_current_profit Trade current profit in {promyq.home_currency}",
        "# TYPE trade_current_profit gauge",
        "# HELP trade_market_open Is the market for this trade open",
        "# TYPE trade_market_open gauge",
        "# HELP ticker_market_open Is the market for this ticker open",
        "# TYPE ticker_market_open gauge",
        "# HELP ticker_price Current market price for this ticker",
        "# TYPE ticker_price gauge"
    ]

    ticker_list = []
    for this_ticker in promyq.tickers:
        ticker_metrics(ticker_list, this_ticker)

    if len(ticker_list) <= 0:
        return flask.make_response("ERROR: Failed to get ticker metrics", 503)

    trades_list = []
    for acct in promyq.trades:
        this_acct = promyq.trades[acct]
        if "stocks" in this_acct:
            for this_trade in this_acct["stocks"]:
                trade_metrics(promyq, trades_list, acct, this_trade)

    if len(trades_list) <= 0:
        return flask.make_response("ERROR: Failed to get trade metrics", 503)

    return flask.make_response(
        "\n".join(help_list + trades_list + ticker_list) + "\n", 200)


@application.route('/promyq/v1.0/hello', methods=['GET'])
def get_hello():
    resp = flask.make_response(flask.jsonify({"hello": "world"}), 200)
    return resp


def main():
    application.run()


if __name__ == "__main__":
    syslog.syslog("RUNNING WEB/UI")
    main()
