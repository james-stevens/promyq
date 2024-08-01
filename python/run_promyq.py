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
            ticker_prices = yahooquery.Ticker(self.tickers)
            self.prices = ticker_prices.price
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


def trade_metrics(retlist, account_name, this_trade):
    this_price = promyq.prices[this_trade["ticker"]]
    if "regularMarketPrice" not in this_price:
        syslog.syslog(f"ERROR: regularMarketPrice not in - {this_price}")
        return

    current_value = this_price["regularMarketPrice"] * this_trade["quantity"]

    infill_dict = {
        "account": account_name,
        "ticker": this_trade['ticker'],
        "when": this_trade['date_bought']
    }

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
    promyq.get_prices()

    retlist = [
        f"# HELP trade_current_value Trade current value in {promyq.home_currency}",
        "# TYPE trade_current_value gauge",
        f"# HELP trade_current_profit Trade current profit in {promyq.home_currency}",
        "# TYPE trade_current_profit gauge",
        "# HELP trade_market_open Is the market for this trade open",
        "# TYPE trade_market_open gauge"
    ]

    if promyq.prices is None:
        syslog.syslog("ERROR: Failed to get prices")
        return

    for acct in promyq.trades:
        this_acct = promyq.trades[acct]
        acct_name = this_acct['name'] if "name" in this_acct else acct
        if "stocks" in this_acct:
            for this_trade in this_acct["stocks"]:
                if "ticker" in this_trade and this_trade[
                        "ticker"] in promyq.prices:
                    trade_metrics(retlist, acct_name, this_trade)

    resp = flask.make_response("\n".join(retlist) + "\n", 200)
    return resp


@application.route('/promyq/v1.0/hello', methods=['GET'])
def get_hello():
    resp = flask.make_response(flask.jsonify({"hello": "world"}), 200)
    return resp


def main():
    application.run()


if __name__ == "__main__":
    syslog.syslog("RUNNING WEB/UI")
    main()
