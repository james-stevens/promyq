#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import syslog
import yaml
import json
import yahooquery


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
        return self.get_all_prices() and self.get_all_currencies()

    def get_all_prices(self):
        self.prices = None
        try:
            self.prices = yahooquery.Ticker(self.tickers).price
            return True
        except Exception as exc:
            syslog.syslog(f"ERROR: {exc}")
            return False
        return False

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
            return True
        except Exception as exc:
            syslog.syslog(f"ERROR: {exc}")
            return False
        return False


    def ticker_metrics(self, retlist, this_ticker):
        if this_ticker not in self.prices:
            return

        this_price = self.prices[this_ticker]
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
        if "tags" in self.trades and this_ticker in self.trades["tags"]:
            infill_dict.update(self.trades["tags"][this_ticker])

        infill = "{" + ",".join(
            [f"{idx}:\"{val}\"" for idx, val in infill_dict.items()]) + "} "

        if "regularMarketChange" in this_price:
            retlist.append(f"ticker_day_move{infill}" + format(
                this_price["regularMarketChange"], f".{self.decimal_places}f"))

        retlist.append(
            f"ticker_price{infill}" +
            format(this_price["regularMarketPrice"], f".{self.decimal_places}f"))

        retlist.append(f"ticker_market_open{infill}" +
                       ("1" if this_price['marketState'] == "REGULAR" else "0"))


    def trade_metrics(self, retlist, acct, this_trade):
        if "ticker" not in this_trade:
            return

        this_ticker = this_trade["ticker"]
        if this_ticker not in self.prices:
            return

        this_price = self.prices[this_ticker]
        this_acct = self.trades[acct]
        acct_name = this_acct['name'] if "name" in this_acct else acct

        if "regularMarketPrice" not in this_price:
            syslog.syslog(f"ERROR: regularMarketPrice not in - {this_price}")
            return

        current_value = this_price["regularMarketPrice"] * this_trade["quantity"]

        infill_dict = {
            "account": acct_name,
            "ticker": this_ticker,
            "currency": self.home_currency,
            "when": this_trade['date_bought']
        }

        # user applied tags
        if "tags" in this_acct:
            infill_dict.update(this_acct["tags"])
        if "tags" in this_trade:
            infill_dict.update(this_trade["tags"])
        if "tags" in self.trades and this_ticker in self.trades["tags"]:
            infill_dict.update(self.trades["tags"][this_ticker])

        infill = "{" + ",".join(
            [f"{idx}:\"{val}\"" for idx, val in infill_dict.items()]) + "} "

        retlist.append(f"trade_market_open{infill}" +
                       ("1" if this_price['marketState'] == "REGULAR" else "0"))
        retlist.append(f"trade_current_value{infill}" +
                       format(current_value, f".{self.decimal_places}f"))
        retlist.append(f"trade_current_profit{infill}" +
                       format(current_value - this_trade["total_cost"],
                              f".{self.decimal_places}f"))

    def get_help_list(self):
        return [
            f"# HELP trade_current_value Trade current value in {self.home_currency}",
            "# TYPE trade_current_value gauge",
            f"# HELP trade_current_profit Trade current profit in {self.home_currency}",
            "# TYPE trade_current_profit gauge",
            "# HELP trade_market_open Is the market for this trade open",
            "# TYPE trade_market_open gauge",
            "# HELP ticker_market_open Is the market for this ticker open",
            "# TYPE ticker_market_open gauge",
            "# HELP ticker_price Current market price for this ticker",
            "# TYPE ticker_price gauge"
        ]

    def trades_list_all(self):
        trades_list = []
        for acct in self.trades:
            this_acct = self.trades[acct]
            if "stocks" in this_acct:
                for this_trade in this_acct["stocks"]:
                    self.trade_metrics(trades_list, acct, this_trade)
        return trades_list

    def tickers_list_all(self):
        ticker_list = []
        for this_ticker in self.tickers:
            self.ticker_metrics(ticker_list, this_ticker)
        return ticker_list



# for debugging only
if __name__ == "__main__":
    my_promyq = PromYQ()
    print(my_promyq.get_prices())
    print("=============")
    print(json.dumps(my_promyq.trades_list_all(),indent=2))
    print("=============")
    print(json.dumps(my_promyq.tickers_list_all(),indent=2))
    print("=============")
    print(json.dumps(my_promyq.rates,indent=2))
