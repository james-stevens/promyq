#! /usr/bin/python3
# (c) Copyright 2019-2024, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import argparse
import syslog
import sys
import os
import yaml
import json
import yahooquery

import log


class PromyqError(Exception):
    pass


def is_forex(ticker):
    return ticker[-2:] == "=X"


class PromYQ:
    def __init__(self):
        self.trades_filename = "/opt/data/etc/promyq.yaml"
        self.cache_filename = "/opt/data/etc/promyq_cache.yaml"
        self.cache_save_required = False
        self.cache = {}
        self.trades = None
        self.prices_want = None
        self.prices_got = None
        self.forex_want = None
        self.forex_got = None
        self.home_currency = "USD"
        self.decimal_places = 2
        self.log_facility = syslog.LOG_LOCAL1
        self.log_severity = syslog.LOG_INFO

    def set_logging(self):
        if "PROMYQ_FACILITY" in os.environ and os.environ["PROMYQ_FACILITY"] in log.facility_options:
            self.log_facility = log.facility_options[os.environ["PROMYQ_FACILITY"]]
            syslog.openlog(logoption=syslog.LOG_PID, facility=self.log_facility)

        if "PROMYQ_SEVERITY" in os.environ and os.environ["PROMYQ_SEVERITY"] in log.severity_options:
            self.log_severity = log.severity_options[os.environ["PROMYQ_SEVERITY"]]

    def prometheus_metrics(self):
        self.set_logging()
        self.load_file()
        self.get_all_tickers()
        self.get_all_prices()
        self.get_all_forex()
        self.all_data_ok()

        ticker_list = self.tickers_list_all()
        if len(ticker_list) < len(self.prices_want):
            raise PromyqError("ERROR: Too few ticker metrics")
        trades_list = self.trades_list_all()
        if len(trades_list) < len(self.trades):
            raise PromyqError("ERROR: Too few trades metrics")
        self.end_service()
        return self.get_help_list() + trades_list + ticker_list

    def end_service(self):
        if not self.cache_save_required or self.forex_want is None:
            return
        data = {"forex": [p[3:6] for p in self.forex_want]}
        with open(self.cache_filename, "w") as fd:
            yaml.dump(data, fd, default_flow_style=False)

    def load_file(self):
        with open(self.trades_filename) as fd:
            self.trades = yaml.load(fd.read(), Loader=yaml.FullLoader)

        if "currency" in self.trades:
            cur = self.trades["currency"]
            if "places" in cur and isinstance(cur["places"], int):
                self.decimal_places = cur["places"]
            if "ticker" in cur:
                self.home_currency = cur["ticker"]

        if not os.path.isfile(self.cache_filename) or os.path.getmtime(self.trades_filename) > os.path.getmtime(
                self.cache_filename):
            self.cache_save_required = True
        else:
            with open(self.cache_filename) as fd:
                this_cache = yaml.load(fd.read(), Loader=yaml.FullLoader)
            if "forex" in this_cache:
                self.forex_want = [self.forex_ticker(p) for p in this_cache["forex"]]

    def forex_ticker(self, currency):
        return self.home_currency + currency + "=X"

    def all_data_ok(self):
        # check we have all the data we wanted
        if self.prices_got is None or len(self.prices_got) < len(self.prices_want):
            raise PromyqError("ERROR: prices_got NONE or too small")

        for ticker in self.prices_want:
            if ticker not in self.prices_got or "regularMarketPrice" not in self.prices_got[ticker]:
                raise PromyqError(f"ERROR: Required ticker {ticker} missing or has no regularMarketPrice")

        if self.forex_want is None or len(self.forex_want) == 0:
            return
        if self.forex_got is None or len(self.forex_got) < len(self.forex_want):
            raise PromyqError("ERROR: forex_got NONE or too small")

        for cur in self.forex_want:
            if cur not in self.forex_got or "regularMarketPrice" not in self.forex_got[cur]:
                raise PromyqError(f"ERROR: Required forex {ticker} missing or has no regularMarketPrice")
        return

    def home_price(self, price, currency):
        # "GBp": price in pence, "GBP": price in pounds
        # when we do currency conversions we need it in pounds
        if currency == "GBp":
            currency = "GBP"
            price = price / 100

        if currency == self.home_currency:
            return price, currency

        forex = self.forex_ticker(currency)
        if forex not in self.forex_got or "regularMarketPrice" not in self.forex_got[forex]:
            return None, None
        return price / self.forex_got[forex]["regularMarketPrice"], self.home_currency

    def get_all_prices(self):
        self.prices_got = None
        try:
            self.prices_got = yahooquery.Ticker(self.prices_want).price
            return
        except Exception as exc:
            syslog.syslog(self.log_severity, str(exc))
        raise PromyqError("ERROR: Yahoo query failed to fetch prices")

    def get_all_tickers(self):
        self.prices_want = None
        all_tickers = {}
        for acct in self.trades:
            if "stocks" in self.trades[acct]:
                for this_trade in self.trades[acct]["stocks"]:
                    if "ticker" in this_trade:
                        all_tickers[this_trade["ticker"]] = True

        if self.forex_want is not None:
            for p in self.forex_want:
                all_tickers[p] = True

        self.prices_want = list(all_tickers)

    def get_all_forex(self):
        if self.forex_want is not None and not self.cache_save_required:
            self.forex_got = {p: self.prices_got[p] for p in self.prices_got if is_forex(p)}
            return

        p_dict = {
            self.prices_got[p]["currency"].upper(): True
            for p in self.prices_got if "currency" in self.prices_got[p]
        }

        self.forex_want = [self.forex_ticker(p) for p in p_dict if p != self.home_currency]
        if len(self.forex_want) <= 0:
            self.forex_got = {}
            return

        self.forex_got = None
        try:
            self.forex_got = yahooquery.Ticker(self.forex_want).price
            return
        except Exception as exc:
            syslog.syslog(self.log_severity, str(exc))
        raise PromyqError("ERROR: Yahoo query failed to fetch forex")

    def ticker_metrics(self, retlist, this_ticker):
        if this_ticker not in self.prices_got or is_forex(this_ticker):
            return

        this_price = self.prices_got[this_ticker]
        if "regularMarketPrice" not in this_price:
            return

        infill_dict = {"ticker": this_ticker}
        if "longName" in this_price:
            infill_dict["name"] = this_price["longName"]
        if "currency" in this_price:
            infill_dict["currency"] = this_price["currency"]

        # user applied tags
        if "tags" in self.trades and this_ticker in self.trades["tags"]:
            infill_dict.update(self.trades["tags"][this_ticker])

        infill = "{" + ",".join([f"{idx}=\"{val}\"" for idx, val in infill_dict.items()]) + "} "

        if "regularMarketChange" in this_price:
            retlist.append(f"ticker_day_move{infill}" +
                           format(this_price["regularMarketChange"], f".{self.decimal_places}f"))

        retlist.append(f"ticker_price{infill}" + format(this_price["regularMarketPrice"], f".{self.decimal_places}f"))
        retlist.append(f"ticker_market_open{infill}" + ("1" if this_price['marketState'] == "REGULAR" else "0"))

    def trade_metrics(self, retlist, acct, this_trade):
        if "ticker" not in this_trade:
            return

        this_ticker = this_trade["ticker"]
        if this_ticker not in self.prices_got:
            return

        this_price = self.prices_got[this_ticker]
        this_acct = self.trades[acct]
        acct_name = this_acct['name'] if "name" in this_acct else acct

        if "regularMarketPrice" not in this_price:
            syslog.syslog(self.log_severity, f"ERROR: regularMarketPrice not in - {this_price}")
            return

        this_value, this_currency = self.home_price(this_price["regularMarketPrice"] * this_trade["quantity"],
                                                    this_price["currency"])

        # currency convertion failed, prob
        if this_value is None or this_currency is None:
            syslog.syslog(self.log_severity, f"ERROR: currency conversion for {this_price['ticker']} failed")
            return

        infill_dict = {
            "account": acct_name,
            "ticker": this_ticker,
            "currency": this_currency,
            "when": this_trade['date_bought']
        }

        if "total_cost" in this_trade:
            infill_dict["total_cost"] = format(this_trade["total_cost"], f".{self.decimal_places}f")

        # user applied tags
        if "tags" in this_acct:
            infill_dict.update(this_acct["tags"])
        if "tags" in this_trade:
            infill_dict.update(this_trade["tags"])
        if "tags" in self.trades and this_ticker in self.trades["tags"]:
            infill_dict.update(self.trades["tags"][this_ticker])

        infill = "{" + ",".join([f"{idx}=\"{val}\"" for idx, val in infill_dict.items()]) + "} "

        retlist.append(f"trade_market_open{infill}" + ("1" if this_price['marketState'] == "REGULAR" else "0"))

        retlist.append(f"trade_current_value{infill}" + format(this_value, f".{self.decimal_places}f"))

        if "total_cost" in this_trade:
            retlist.append(f"trade_current_profit{infill}" +
                           format(this_value - this_trade["total_cost"], f".{self.decimal_places}f"))

    def get_help_list(self):
        return [
            f"# HELP trade_current_value Trade current value in {self.home_currency}",
            "# TYPE trade_current_value gauge",
            f"# HELP trade_current_profit Trade current profit in {self.home_currency}",
            "# TYPE trade_current_profit gauge", "# HELP trade_market_open Is the market for this trade open",
            "# TYPE trade_market_open gauge", "# HELP ticker_market_open Is the market for this ticker open",
            "# TYPE ticker_market_open gauge", "# HELP ticker_price Current market price for this ticker",
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
        for this_ticker in self.prices_want:
            self.ticker_metrics(ticker_list, this_ticker)
        return ticker_list


# for debugging only
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PromYQ Run')
    parser.add_argument("-j", '--json', action="store_true")
    args = parser.parse_args()

    my_promyq = PromYQ()
    try:
        prom_metrics = my_promyq.prometheus_metrics()
        if args.json:
            print(
                json.dumps({
                    "trades": my_promyq.trades,
                    "prices": my_promyq.prices_got,
                    "forex": my_promyq.forex_got
                },
                           indent=2))
        else:
            print("\n".join(prom_metrics))
    except PromyqError as e:
        print(f"{str(e)}")

    sys.exit(0)
