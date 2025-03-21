#! /usr/bin/python3
#
# for testing / debugging
#

import json

from yahooquery import Ticker

tickers = Ticker(["TSLA", "AAPL"])
print(json.dumps(tickers.price, indent=3))
# print(json.dumps(tickers.summary_detail,indent=3))
print(json.dumps(tickers.major_holders, indent=3))
