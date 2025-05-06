#! /usr/bin/python3

import yahooquery as yq
import json

from curl_cffi import requests

session = requests.Session(impersonate="chrome")

tickers = yq.Ticker(["TSLA", "AAPL"], session=session)

print(json.dumps(tickers.price, indent=3))
print(json.dumps(tickers.major_holders, indent=3))
