# make buy sell distinction between stocks purchased for daytrading and long term purchases

import threading
import time
from datetime import datetime
from pytz import timezone

import alpaca as alp
import constants as const
import news_classifier as nc
import news_getter
import scraper
import stock_analysis as sa
import stock_data_gatherer as sdg
import util


def calculate_order_amount(stock_ticker, stock_score):
    symbol_bars = alpaca.api.get_barset(stock_ticker, 'minute', 1).df.iloc[0]
    symbol_price = float(symbol_bars[stock_ticker]['close'])
    buying_power = float(alpaca.api.get_account().buying_power)
    order_amount = (buying_power*stock_score)//symbol_price
    return order_amount

def daytrading_stock_analyzer(stocks):
    for stock_ticker in stocks:  # purchases stocks based on daytrading patterns
        try:
            stock_score = 0
            stock_score += sa.moving_average_checker(stock_ticker)
            stock_score += sa.volume_checker(stock_ticker)
            if stock_score >= 0.2 and stock_ticker not in all_active_positions.keys():
                order_amount = calculate_order_amount(stock_ticker, stock_score)
                alpaca.create_order(stock_ticker, order_amount)  # todo: calculate order amount
                active_positions_to_check[stock_ticker] = sdg.get_current_stock_data(stock_ticker)["Close"]
                all_active_positions[stock_ticker] = sdg.get_current_stock_data(stock_ticker)["Close"]
                print("Based on daytrading pattern analysis, buying", stock_ticker, "Stock Score: ", stock_score)
        except Exception as e:
            print(f"daytrading_stock_analyzer error: {e}")
            pass


def news_stock_analyzer(stock_ticker):
    try:
        stock_score = 0
        stock_score += nc.sentiment_analyzer(news.get_news(stock_ticker))
        print(stock_ticker, "news score:", stock_score)
        if stock_score >= 0.35 and stock_ticker not in all_active_positions.keys():
            order_amount = calculate_order_amount(stock_ticker, stock_score)
            alpaca.create_order(stock_ticker, order_amount)  # todo: calculate order amount
            active_positions_to_check[stock_ticker] = sdg.get_current_stock_data(stock_ticker)["Close"]
            all_active_positions[stock_ticker] = sdg.get_current_stock_data(stock_ticker)["Close"]
            print("Based on News analysis, buying", stock_ticker)
    except Exception as e:
        print(f"news_stock_analyzer error for {stock_ticker}: {e}")


def stock_position_analyzer():
    while True:
        for position in active_positions_to_check.keys():
            threading.Thread(target=check_perform_sell, args=(position, active_positions_to_check[position])).start()
        active_positions_to_check.clear()


def check_perform_sell(stock_ticker, purchase_price):
    while True:
        current_stock_price = sdg.get_current_stock_data(stock_ticker)["Close"]
        price_change_percent = util.calculate_price_change(current_stock_price, all_active_positions[stock_ticker])
        print("Checking", stock_ticker, "Gains/Losses", price_change_percent, "Price: $", current_stock_price)
        if (
            sa.moving_average_checker(stock_ticker) < 0
            or price_change_percent <= -const.MAX_STOP_LOSS_PERCENT
            or sa.volume_checker(stock_ticker) < 0
        ):
            alpaca.sell_position(stock_ticker)
            del all_active_positions[stock_ticker]
            break


if __name__ == "__main__":

    # Initializing important stuff
    tz=timezone('US/Eastern')
    news = news_getter.NewsGetter()
    alpaca = alp.Alpaca()
    active_positions_to_check = {}  # key is stock ticker, value is stock purchase price
    all_active_positions = {}  # key is stock ticker, value is stock purchase price
    positions = alpaca.get_positions()
    for position in positions:  # todo also add orders
        active_positions_to_check[position.symbol] = float(position.cost_basis)  # cost basis not working well

    all_active_positions = active_positions_to_check.copy()
    print("Currently Purchased:", active_positions_to_check)
    first_time_run = True

    while True:
        try:
            print("New Iteration of Stock Scanning")
            current_time = datetime.now(tz).strftime("%H:%M")
            if alpaca.api.get_clock().is_open and current_time < const.STOCK_MARKET_CLOSE_TIME:
                if first_time_run:
                    threading.Thread(target=stock_position_analyzer).start()
                    first_time_run = False
                active_stocks = scraper.active_stocks()
                partitioned_stocks = util.partition_array(active_stocks, const.STOCK_SCANNER_PARTITION_COUNT)
                for partition in partitioned_stocks:
                    threading.Thread(target=daytrading_stock_analyzer, args=[partition]).start()
            else:
                alpaca.sell_all_positions()
                print("Market Close")
                for stock_ticker in const.STOCKS_TO_CHECK:  # purchases stocks based on news info
                    news_stock_analyzer(stock_ticker)
                    # threading.Thread(target=news_stock_analyzer, args=(stock_ticker,)).start()
                time.sleep(360000)
        except Exception as e:
            print(f"__main__ error: {e}")
            print("Restarting")
