# PromYQ - An Asset Portfolio Tracker

PromYQ is a container for tracking the value of a collection of asset portfolios. It gets the prices using YahooQuery, so can price anything tracked by Yahoo Finance, this includes most global stocks (equities),
 a range of the major crypto currencies and various stores of wealth like precious metals.

If your home currency does not match the currency the asset is priced in, it will pull a live
exchange rate and calculate the currency value in your configured home currency.

The tracking & historic value storage is done by Prometheus and the visualisation is with Grafana, both are included in the container and both offer a wide range of other 3rd party integrations.

Configuration, of the trades you wish to track, is via a YAML file, which is read every time time Prometheus polls for the current prices - so any changes will be reflected at the next poll interval. This interval is user configurable at runtime.

Apart from the list of trades you wish to track, there are really only two things you can configure – ow often to poll and how long to retain historic data - often call refresh interval & retention time.

A demo portfolio configuration file and two demo Grafana dashboards are included in the container.


## Supported Environment Variables

| Env Var | Default | Meaning
|---------|--------|----------|
| PROMYQ_REFRESH_INTERVAL | 5 mins | How often Prometheus will poll for the current price
| PROMYQ_RETENTION_TIME | 180 days | How long Prometheus will retain historic data
| PROMYQ_FACILITY | local1 | Syslog “facility” to log to
| PROMYQ_SEVERITY | info | Syslog “severity” to log with
| SYSLOG_SERVER | Console | IP Address to syslog to

By default the container will log to the "console" / "standard output", but if you wish to log to a syslog server, you can do this by setting the environment variable `SYSLOG_SERVER` to the IP Address of your syslog server.

The format of the refresh interval & retention time supports the units: y, w, d, h, m, s, ms - e.g. `5m` or `180d`.


## Data Storage

All the Prometheus and Grafana data will be stored in the directory `/opt/data`. If you wish your data to be persistent (be retained over a restart), you will need to map into this directory some long term storage space.

How you do this will depend on your environment, so is outside the scope of this document.

The first time the container is run, Prometheus and Grafana will both set up their databases in the storage space you have provided - this can take a bit of time, but only happens the first time.


## Configuration File

The YAML configuration file is stored at `/usr/local/etc/promyq.yaml`. There is a simple demo file provided in the container, but you will want to manifest your own file to this location so it tracks your trades.

How you do this will depend on your environment, so is outside the scope of this document.

The file is read every time Prometheus polls for prices, so any changes you make will be reflected at the next polling interval.

Optional global properties are `currency` which can have the properties `ticker` (ISO currency id, default `USD`) and `places` for the number of decimal places you want to round to, default 2.

The file consists of a series of account objects, which can each have a optional description property called `name` and a mandatory property called `stocks` which is a list of the trades you wish to track.

Each trade must have the mandatory fields `ticker`, `date_bought` and `quantity` and the optional field `total_cost` (the original cost of the trade in your home currency).
 You can add as many other properties to a trade as you like, but these are the only ones that are used.

If you include `total_cost` then you will also get a metric `trade_current_profit`, which will be the current profit / loss you are making on that trade.

The `date_bought` field will be added as a tag to every trade metric so trades on the same ticker can be uniquely identified.

A minimum file might look like this

	account_name:
		name: "Account Description"
		stocks:
		  - ticker: TSLA
			date_bought: 2024-01-01 01:01:01
			quantity: 27
			total_cost: 1234.67

This defines an account called `account_name` which holds a single trade in `TSLA` stock.

Tickers can be found through the Yahoo Finance website. Crypto currencies tickers are typically `<Crypto>-USD`, e.g. `BTC-USD`. All tickers you find through the Yahoo Finance website should work, e.g Gold is `GC=F`.


## Custom Tags

In Prometheus / Grafana tags are a way to group, filter or describe metrics. 

Each trade will be tagged with its account, ticker, date and currency, but you can add your own tags to account, trades or tickers – using the property “tags”. Spot prices will be tagged with the ticker, its description (as supplied by Yahoo) and its currency.

This means, for example, you can graph total value by account, or total value by ticker – both these dashboard are included as demos.

You can add your own tags to each account, trade or by ticker using the property `tags`.

`tags` at the global level is for adding tags to all trades or spot prices for the same ticker. For example, this YAML at the global level will add the tag `sector=”automotive”` to every spot price or trade metric for Tesla stock.

	tags:
		TSLA:
			sector: automotive

By adding a `sector` tag to all your stocks, you could then graph total value by sector of your portfolio.


## Port and Services

There are three levels of service from the container giving increasing levels of sophistication. All are HTTP (not HTTPS).
If you want any of the services from this container exposed to the public internet, I strongly recommend (as a minimum)
you access this container through an HTTPS proxy (e.g. nginx). If you are only accessing this container over a private network, this may not be necessary.

There is only built-in authentication (logins) on port 3000 (Grafana). Prometheus comes with zero authentication – if the port is accessible, anybody can access it.


### Port 8000

This port runs the python/flask code that generates the original metrics to feed to Prometheus. If you wish to feed the Prometheus style metrics into a different application, you can poll them from this port.

### Port 9090

This is the default port for Prometheus. Prometheus provides both a WebUI and a GraphQL service from this port. If you wish to query the Prometheus database from a different application, you can access it from this port.


### Port 3000

This is the default port for Grafana. The default account is `admin`, default password `admin`, but it will force you to change the password when you first log in. Once you have logged in, you can create additional users.

You should find two demo dashboards but obviously you can make as many as you like and Grafana will store them in the data storage space you provided. They can also be exported as JSON.

Not only can Grafana give you live scrolling graphs, pie charts & heat maps of activity, but it can also provide tables of trade value movements by percent or absolute value over a time scale of your selection.


## The Metrics

These are the Prometheus metrics it will generate

### For each Trade

		# HELP trade_current_value Trade current value in <home-currency>
		# TYPE trade_current_value gauge
		# HELP trade_current_profit Trade current profit in <home-currency>
		# TYPE trade_current_profit gauge
		# HELP trade_market_open Is the market for this trade open
		# TYPE trade_market_open gauge

### For Each Ticker

		# HELP ticker_market_open Is the market for this ticker open
		# TYPE ticker_market_open gauge
		# HELP ticker_price Current market price for this ticker
		# TYPE ticker_price gauge
