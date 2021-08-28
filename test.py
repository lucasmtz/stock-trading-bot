import news_getter

import constants
import news_classifier

b = news_getter.NewsGetter()

for ticker in constants.STOCKS_TO_CHECK:
    print("Ticker Symbol", ticker, "Stock score:", news_classifier.sentiment_analyzer(b.get_news(ticker)))
