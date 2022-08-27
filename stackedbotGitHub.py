import talib, time, json, requests
from decimal import Decimal
import numpy as np
from binance.client import Client
from binance.websockets import BinanceSocketManager

binance_coin = 'LTCUSDT'

api_key_in = '' #Need your own here
api_secret_in = '' #Need your own here


#JSON messages that were sent to Stacked
# AuthCode has been removed from the JSON messages
openlong = {
  "symbol": "LTC/USD",
  "authCode": "",
  "side": "buy",
  "action": "open",
  "equity": 100
}

openshort = {
  "symbol": "LTC/USD",
  "authCode": "",
  "side": "sell",
  "action": "open",
  "equity": 100
}

closeall = {
  "symbol": "LTC/USD",
  "authCode": "",
  "side": "all",
  "action": "close"
}

jsonlong = json.dumps(openlong)
jsonshort = json.dumps(openshort)
jsonclose = json.dumps(closeall)


class Process: # TO READ MESSAGES FROM THE LIVE DATA SOCKET
    
    def process_message(self, msg):
        # print("message type: {}".format(msg['e']))
        self.msg = msg
        if self.msg['k']['x'] == True:
            self.lasthighs.append(float(self.msg['k']['h']))
            self.lastlows.append(float(self.msg['k']['l']))
            self.lastcloses.append(float(self.msg['k']['c']))
    
    def process_mark(self, markmsg):
        self.mark = markmsg
        self.markprice = float(self.mark['data']['p'])

        self.lst_of_price[0] = self.markprice

class GetBinanceClient(Process):

    def __init__(self, api_key, api_secret): # IGNORE THIS, MAKING INITIAL LISTS
        self.lsthighs = []
        self.lstlows = []
        self.lstcloses = []
        self.lst_of_price = [0]

        self.api_key = api_key
        self.api_secret = api_secret

    def b_getclient(self): # CREATES WEBSOCKET
        self.client = Client(self.api_key, self.api_secret)
        self.bm = BinanceSocketManager(self.client)

    def b_getdata(self): # STARTS DATAFEED
        self.bm.start_kline_socket(binance_coin, super().process_message, interval = Client.KLINE_INTERVAL_4HOUR)
        self.bm.start_symbol_mark_price_socket(binance_coin, super().process_mark, fast = False)
        self.bm.start()   

    def b_get_market_price(self):
        self.market_price = self.lst_of_price[0]
        return self.market_price

    def b_get_funding_rate(self):
        self.funding_lib = self.client.futures_funding_rate(symbol = binance_coin, limit = 1)
        self.funding_rate = float(self.funding_lib[0]['fundingRate']) * 100
        return self.funding_rate

    def b_getpastdata(self): # GETS PAST KLINES TO USE FOR INITIAL DATA
        self.candles = self.client.futures_klines(symbol=binance_coin, interval = Client.KLINE_INTERVAL_4HOUR)
        for data in self.candles:
            highs = float(data[2])
            lows = float(data[3])
            closes = float(data[4])

            self.lsthighs.append(highs)
            self.lstlows.append(lows)
            self.lstcloses.append(closes)
        
        self.lsthighs.pop(-1)
        self.lstlows.pop(-1)
        self.lstcloses.pop(-1)

        self.lastcloses = self.lstcloses[-50:]
        self.lasthighs = self.lsthighs[-50:]
        self.lastlows = self.lstlows[-50:]
        
        del self.lstcloses
        del self.lsthighs
        del self.lstlows

    def b_get_rsi_stoch(self): #For updating RSI/STOCH based on incoming data
        self.lastcloses = self.lastcloses

        self.np_closes = np.array(self.lastcloses[-50:])
        self.np_highs = np.array(self.lasthighs[-50:])
        self.np_lows = np.array(self.lastlows[-50:])

        self.b_slowk, self.b_slowd = talib.STOCH(self.np_highs, self.np_lows, self.np_closes, 8, 3, 0, 3, 0)
        self.b_rsi = talib.RSI(self.np_closes, 14)
        self.b_realslowk = round(self.b_slowk[-1], 2)
        self.b_realrsi = round(self.b_rsi[-1], 2)

        return self.b_realslowk, self.b_realrsi



binance = GetBinanceClient(api_key_in,
 api_secret_in)

sidelng = False
sideshrt = False
orderplaced = False
threshold = False
fund_check = False

candle_rsi = 0
count = 5

max_tries = 0

binance.b_getclient()
binance.b_getpastdata()
binance.b_getdata()




print("CONNECTION SUCCESSFUL")
time.sleep(5)
while max_tries < 5:
    markprice = binance.b_get_market_price()

    stochk, rsi = binance.b_get_rsi_stoch()

    price = float(markprice)


    if sidelng == False and sideshrt == False and orderplaced == False and count >= 5:


        #The "0"s indicate strategy. Real indicator numbers have been taken out
        if stochk > 0 and rsi < 0 and fund_check == False:
            funding_rate = binance.b_get_funding_rate()
            if funding_rate < 0.001:
                sideshrt = True
                orderplaced = True
                candle_rsi = float(rsi)
                count = 0

                shrt_entry = price

                shrtcall = price + (price * 0.03)
                shrt_threshold = price - (price * 0.0375)
                x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonshort.encode('utf-8'), verify=False, headers={"Content-Type": "application/json"},timeout=10.0)

                while x.status_code > 200:
                        max_tries += 1
                        if x.status_code == 200:
                            break
                        else:
                            x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonshort.encode('utf-8'), verify=False, headers={"Content-Type": "application/json"},timeout=10.0)
                            print('SHORT POSITION OPENED. SENT DATA TO STACKED')
                            print(x.status_code, x.reason)
                            print(x)
                        time.sleep(30)
                
                
                print('SHORT POSITION OPENED. SENT DATA TO STACKED')
                print(x.status_code, x.reason)
                print(x)
                print('FundRate: ',funding_rate, '\nStock and RSI: ', stochk, rsi)
            else:
                print("Funding rate too high! You wanna lose money?")
                time.sleep(14400)
                fund_check = True
                pass
            
        

                #The "0"s indicate strategy. Real indicator numbers have been taken out
        elif stochk <0 and rsi > 0 and fund_check == False:
            funding_rate = binance.b_get_funding_rate()
            if funding_rate >= 0.001:
                sidelng = True
                orderplaced = True
                candle_rsi = float(rsi)
                count = 0

                lng_entry = price

                lngcall = price - (price * 0.03)
                lng_threshold = price + (price * 0.0375)
                x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonlong.encode('utf-8'), verify=False,headers={"Content-Type": "application/json"},timeout=10.0)
                
                while x.status_code > 200:
                        max_tries += 1
                        if x.status_code == 200:
                            break
                        else:
                            x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonlong.encode('utf-8'), verify=False, headers={"Content-Type": "application/json"},timeout=10.0)
                            print('LONG POSITION OPENED. SENT DATA TO STACKED')
                            print(x.status_code, x.reason)
                            print(x)
                        time.sleep(30)

                print('LONG POSITION OPENED. SENT DATA TO STACKED')
                print(x.status_code, x.reason)
                print(x)
                print('FundRate: ',funding_rate, '\nStock and RSI: ', stochk, rsi)
            else:
                print("Bro the funding rate says you'll lose money, dont be stupid foo")
                fund_check = True
                time.sleep(14400)
                pass
            
    
    elif orderplaced == True:

        if sidelng == True:

            if price >= lng_threshold:
                threshold = True   
            
            if price <= lngcall: # close the long position
                x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonclose.encode('utf-8'), verify=False,headers={"Content-Type": "application/json"},timeout=10.0)
                print('POSITION CLOSED. SENT DATA TO STACKED')
                print(x.status_code, x.reason)
                print(x)
                sidelng = False
                orderplaced = False
                threshold = False


                while x.status_code > 200:
                    if x.status_code == 200:
                        break
                    else:
                        x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonclose.encode('utf-8'), verify=False,headers={"Content-Type": "application/json"},timeout=10.0)
                        print('POSITION CLOSED. SENT DATA TO STACKED')
                        print(x.status_code, x.reason)
                    time.sleep(60)

                    

            elif threshold == True:
                if price > lng_entry:
                    lngcall = price - (price * 0.03)
                    lng_entry = price




        elif sideshrt == True:

            if shrt_threshold >= price:
                threshold = True    

            if price >= shrtcall: # close the short position
                x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonclose.encode('utf-8'), verify=False,headers={"Content-Type": "application/json"},timeout=10.0)
                print('POSITION CLOSED. SENT DATA TO STACKED')
                print(x.status_code, x.reason)
                print(x)
                sideshrt = False
                orderplaced = False
                threshold = False


                while x.status_code > 200:
                    if x.status_code == 200:
                        break
                    else:
                        x = requests.post('https://alerts.stackedinvest.com/api/v1/alert', jsonclose.encode('utf-8'), verify=False,headers={"Content-Type": "application/json"},timeout=10.0)
                        print('POSITION CLOSED. SENT DATA TO STACKED')
                        print(x.status_code, x.reason)
                    time.sleep(60)

            elif threshold == True:
                if price < shrt_threshold:
                    shrtcall = price + (price* 0.03)
                    shrt_entry = price

            else: pass

                
    if candle_rsi == rsi:
        pass
    elif candle_rsi != rsi:
        count += 1
        candle_rsi = rsi
        fund_check = False
    

    time.sleep(60)
