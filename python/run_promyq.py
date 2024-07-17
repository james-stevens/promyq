#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import flask
import syslog
import yaml
import yahooquery

application = flask.Flask("PromYQ")
with open("/usr/local/etc/promyq.yaml") as fd:
    trades = yaml.load(fd.read(), Loader=yaml.FullLoader)

home_currency = trades["home_currency"] if "home_currency" in trades else "USD"
decimal_places = trades["places"] if "places" in trades else 2


def get_prices(ticker):
    try:
        tickers = yahooquery.Ticker(ticker)
        return tickers.price
    except Exception as exc:
        print(f"ERROR: {exc}")
        return None
    return None


def get_all_tickers():
    all_tickers = {}
    for acct in trades:
        if "stocks" in trades[acct]:
            for this_trade in trades[acct]["stocks"]:
                if "ticker" in this_trade:
                    all_tickers[this_trade["ticker"]] = True
    return list(all_tickers)


def get_all_prices():
    return get_prices(get_all_tickers())


def process_item(retlist, account_name, this_trade, this_price):
    if "regularMarketPrice" not in this_price:
        print(">>>>> ERROR: regularMarketPrice not in ",this_price)
        return

    current_value = this_price["regularMarketPrice"] * this_trade["quantity"]

    infill = ("{" + f"account=\"{account_name}\"," +
              f"ticker=\"{this_trade['ticker']}\"," +
              f"when=\"{this_trade['date_bought']}\"" + "} ")

    retlist.append(f"trade_market_open{infill}" +
                   ("1" if this_price['marketState'] == "REGULAR" else "0"))
    retlist.append(f"trade_current_value{infill}" +
                   format(current_value, f".{decimal_places}f"))
    retlist.append(f"trade_current_profit{infill}" +
                   format(current_value -
                          this_trade["total_cost"], f".{decimal_places}f"))


@application.route('/metrics', methods=['GET'])
def get_metrics():
    all_prices = get_all_prices()
    retlist = [
        f"# HELP trade_current_value Trade current value in {home_currency}",
        "# TYPE trade_current_value gauge",
        f"# HELP trade_current_profit Trade current profit in {home_currency}",
        "# TYPE trade_current_profit gauge",
        "# HELP trade_market_open Is the market for this trade open",
        "# TYPE trade_market_open gauge"
    ]

    for acct in trades:
        if "stocks" in trades[acct]:
            for this_trade in trades[acct]["stocks"]:
                if "ticker" in this_trade and this_trade[
                        "ticker"] in all_prices:
                    process_item(retlist, trades[acct]['name'], this_trade,
                                 all_prices[this_trade["ticker"]])
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
