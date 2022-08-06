import threading
import pyupbit
import numpy as np
from datetime import datetime
from pandas import DataFrame
import pandas as pd
import time
import warnings
from flask import Flask

app = Flask(__name__)


progress = 0
money = 0

class Wallet:
    money = 10000000
    balances = DataFrame(columns=['name', 'price_order', 'balance', 'cnt_buy'])
    def GetInfo(this, target):
        try:
            idx = list(this.balances['name'].values).index(target)
        except ValueError:
            #print('\'{}\' not found '.format(target))
            return [False, None]
        return [True, this.balances.loc[idx]]
    def Buy(this, target, price_current, price_order):
        print('#Buy')
        if this.money < 5000:
            print('Not enough money to buy')
            return False

        if price_order < 5000:
            price_order = 5000
        elif price_order > this.money:
            price_order = this.money
        price_order = price_order*0.9995
        fee = price_order*0.0005

        quantity_buy = price_order/price_current
        
        try:
            idx = list(this.balances['name'].values).index(target)
            this.balances.loc[idx, 'balance'] += quantity_buy
            this.balances.loc[idx, 'price_order'] += price_order
            this.balances.loc[idx, 'cnt_buy'] += 1
            print('기존에 구매했던 코인 :: 구매횟수 증가!! ', this.balances.loc[idx]['cnt_buy'])
        except ValueError:
            print('첫 구매 코인!!')
            this.balances = this.balances.append({'name' : target, 'price_order': price_order, 'balance' : quantity_buy, 'cnt_buy' : 1}, ignore_index=True)
        this.money -= (price_order + fee)
        this.ViewBalance(target, price_current)
        
    def Sell(this, target, price_current, sell_ratio):
        print('#Sell')
        sell_ratio = sell_ratio/100
        try:
            idx = list(this.balances['name'].values).index(target)
        except ValueError:
            print('You don\'t have [{}]'.format(target))
            return False
        blc = this.balances.loc[idx]['balance']
        prc_ord = this.balances.loc[idx]['price_order']
        prc_mrk = blc * price_current
        quantity_sell = blc * sell_ratio
        price_sell = prc_mrk * sell_ratio
        #보유량이 5000원보다 큰데, 판매하려는 양은 5000원보다 작다면
        if blc * price_current > 5000 and blc * sell_ratio * price_current < 5000 :
            #판매하려는 양을 5000원으로 설정
            quantity_sell = 5000/price_current
            price_sell = 5000
        if (this.money - price_sell) < 5000:
            quantity_sell = blc
            price_sell = prc_ord
            this.balances.loc[idx, 'cnt_buy'] = 0

        
        this.balances.loc[idx, 'balance'] -= quantity_sell
        this.balances.loc[idx, 'price_order'] -= price_sell
        
        this.money += quantity_sell*price_current*0.9995
        
        if this.balances.loc[idx]['balance'] == 0:
            this.balances = this.balances.drop(this.balances.index[this.balances['name']==target])
        this.ViewBalance(target, price_current)
        
    def ViewBalance(this, target=None, price_current=None):
    #def ViewBalance(this, target=None, price):
        print('#ViewBalnace')
        print('총 보유 원화 : ', this.money, '(원)')
        print('--------'*5)
        if target == None or price_current == None:
            return True
        try:
            idx = list(this.balances['name'].values).index(target)
        except ValueError:
            print('\'{}\' not found '.format(target))
            return False
        blc = this.balances.loc[idx]['balance']
        prc_ord = this.balances.loc[idx]['price_order']
        print('이름 : ', this.balances.loc[idx]['name'])
        print('보유 수량 : ', blc)
        print('구매 금액 : ', prc_ord)
        
        #price_current = pyupbit.get_orderbook(ticker=target)["orderbook_units"][0]["ask_price"]
        #price_equities = blc * price
        price_market = blc * price_current
        print('평가 금액 : ', price_market)
        dif = price_market - prc_ord
        dif_ratio = round((dif/prc_ord)*100, 4)
        print('수익률 : ', dif, '({}%)'.format(dif_ratio))
        print('구매 횟수 : ', this.balances.loc[idx]['cnt_buy'])
        print('--------'*5)

def get_ma(arr, unit="minute", period=30):
    """15일 이동 평균선 조회"""
    #df = pyupbit.get_ohlcv(ticker, interval=unit, count=period)
    global data_backup
    ma15 = arr['close'].rolling(15).mean().iloc[-1]
    return ma15

@app.route("/")
def hello_world():
    global progress, money
    print(progress)
    return "<p>progress : " + str(progress) + "</p><br>money : " + str(money)

wallet = Wallet()

t = threading.Thread(target=app.run, args=('0.0.0.0', 8989))
t.start()

warnings.filterwarnings(action='ignore')
#실시간 받아오는 테스트시 사용
#price_current = pyupbit.get_orderbook(ticker="KRW-BTC")["orderbook_units"][0]["ask_price"]
#data_backup = pyupbit.get_ohlcv("KRW-BTC", count=60*24*62 + 40, interval='minute3')
data_backup = pd.read_excel('data_3m15d.xlsx', index_col=0, engine='openpyxl')
data_backup.rename(columns = {'open':'price'}, inplace = True)

moving_average = get_ma(data_backup[:40])
list_volume = data_backup['volume'][40:]
list_price = data_backup['price'][40:]
list_date = list(map(lambda a : pd.to_datetime(a).date(), data_backup.index.tolist()[40:]))
price_current = list_price[0]
trend = DataFrame(data={'date' : datetime.now().strftime("%y-%m-%d %H:%M:%S"), 'price' : price_current, 'Moving Average' : moving_average, 'dif mov' : price_current - moving_average}, index=[0])

print('@@@')
#time.sleep(20)
delay = 0
cnt_buy = 0
#while True:
#40 전까지는 평균 이동선 구하는데 사용했음.
for i, price_current in enumerate(list_price[1:], start=1):
    progress = round(i/len(list_price), 2)*100
    flag_sell = 0
    buy = ''
    sell = ''
    #실시간 받아오는 테스트시 사용
    #price_current = pyupbit.get_orderbook(ticker="KRW-BTC")["orderbook_units"][0]["ask_price"]
    moving_average = get_ma(data_backup[40+i-1:40+i-1+40])
    #df_appended = DataFrame(data={'date' : datetime.now().strftime("%y-%m-%d %H:%M:%S"), 'price' : price_current}, index=[i])
    df_appended = DataFrame(data={'date' : list_date[i], 'price' : price_current}, index=[i])
    price_previous = trend.loc[i-1]['price']
    change = price_current - price_previous
    df_appended['Delay']= delay
    df_appended['Buy'] = ''
    df_appended['Sell'] =''
    df_appended['Volume'] = list_volume[i]
    #수익률 확인용
    if wallet.GetInfo('KRW-BTC')[0]:
        #price_avg = 현재 매수가
        my_priceOrder = wallet.GetInfo('KRW-BTC')[1]['price_order']
        my_price_market = price_current * wallet.GetInfo('KRW-BTC')[1]['balance']
        #dif_price = 현재 시세와 내 구매가 차이
        price_profit = my_price_market - my_priceOrder
        ratio_profit = round(price_profit/my_priceOrder, 4) * 100
        df_appended['Profit'] = str(ratio_profit) + '%'
        df_appended['Profit_price'] = str(price_profit)
    if False:
    #if wallet.GetInfo('KRW-BTC')[0]:
        my_priceOrder = wallet.GetInfo('KRW-BTC')[1]['price_order']
        my_balance = wallet.GetInfo('KRW-BTC')[1]['balance'] 
        price_market = price_current * my_balance
        #dif_price = 현재 시세와 내 구매가 차이
        dif_price = my_priceOrder - price_market
        dif_ratio = round(dif_price/my_priceOrder, 4) * 100
        wallet.ViewBalance('KRW-BTC', price_current)
        print('평가 금액 : ' + str(my_priceOrder))
        print('my_priceOrder : ' + str(my_priceOrder))
        print('my_balance : ' + str(my_balance))
        print('dif_ratio : ' + str(dif_ratio))
        input('dif_price : ' + str(dif_price))
        df_appended['ratio_profit'] = str(dif_ratio) + '%'
    if change > 0:
        transition = 1
    else:
        transition = 0
    if i>=10:
        price_5prev = trend.loc[i-5]['price']
        price_10prev = trend.loc[i-10]['price']
        price_comp_5prev = price_5prev < price_current
        price_comp_10prev = price_10prev > price_5prev
        df_appended['Moving Average'] = moving_average
        df_appended['dif mov'] = price_current - moving_average

        #매도
        if wallet.GetInfo('KRW-BTC')[0]:
            flag_sell = 1
            #price_avg = 현재 매수가
            my_priceOrder = wallet.GetInfo('KRW-BTC')[1]['price_order']
            my_price_market = price_current * wallet.GetInfo('KRW-BTC')[1]['balance']
            #dif_price = 현재 시세와 내 구매가 차이
            price_profit = my_price_market - my_priceOrder
            ratio_profit = round(price_profit/my_priceOrder, 4) * 100
            # 수익률이 +일 때, 수익금이 천원 이상이면
            if ratio_profit > 0.5:
                change_5m = price_current - price_5prev
                transition_5m = sum(trend.loc[i-5:i]['transition'].values)
                ratio_change_5m = round(change_5m/price_5prev, 4) * 100
                '''
                #5%이상 떨어졌을 때
                if ratio_change_5m < -1:
                    wallet.Sell('KRW-BTC', price_current, (1/3)*100)
                    sell = 'Sell(' + str(1/3) + ')'\
                '''
                #5분 동안 상승중일 때
                #증가율이 높으면 조금 판매? (묵혀놔야되니까?)
                #비트코인처럼 증감폭이 적은건.. 큰폭으로 증가했을 때 판매하는 전략은 별로인듯. 큰폭으로 증가하는 경우가 흔치 않아서
                #계속 떨어짐..
                #if ratio_change_5m >= 1:
                wallet.Sell('KRW-BTC', price_current, 100)
                sell = 'Sell(' + str(100) + '%) '
            #수익률이 -1% 이상 마이너스일 때, 전부 매도
            #일단 해보고.. 거래량이나 추이 고려해서 차등 매도하는 것도 추가해보기로 하자.
            elif ratio_profit <= -2:
            #elif price_profit < -1000:
                    wallet.Sell('KRW-BTC', price_current, 100)
                    sell = 'Sell(' + str(100) + '%) --'

        #매수
        #5분 전까지는 하락세, 5분 이후부터는 상승세일 때 매수
        comp_down = sum(trend.loc[i-10:i-5]['transition'].values) < 3
        comp_up = sum(trend.loc[i-5:i]['transition'].values) >= 2
        
        if ( price_comp_10prev and comp_down ) \
        and ( price_comp_5prev and sum(trend.loc[i-5:i]['transition'].values) >= 2) \
        and ( price_current < moving_average ) \
        and (delay == 0 and flag_sell == 0):
            delay = 5
            try:
                cnt_buy = wallet.GetInfo('KRW-BTC')[1]['cnt_buy']
            except TypeError:
                cnt_buy = 0
            if cnt_buy < 3:
                volume_buy = (wallet.money)*(1/3)
                wallet.Buy('KRW-BTC', price_current, volume_buy)
                buy = 'Buy(' + str(volume_buy) + ')'
            #trend.

    if transition == 1:
        mark_transition = '▲'
    else:
        mark_transition = '▽'
    df_appended['Buy'] = buy
    df_appended['Sell'] = sell
    df_appended['mark_transition'] = mark_transition
    if 'price_10prev' in locals():
        df_appended['comp 10prev'] = price_comp_10prev
        df_appended['comp 5prev'] = price_comp_5prev
        df_appended['comp down'] = comp_down
        df_appended['comp up'] = comp_up
    if wallet.GetInfo('KRW-BTC')[0]:
        my_price_market = price_current * wallet.GetInfo('KRW-BTC')[1]['balance']
        money = my_price_market + wallet.money
        df_appended['money'] = money
    else:
        money = wallet.money
        df_appended['money'] = money
    df_appended['transition'] = transition
    trend = trend.append(df_appended)
    #time.sleep(60)
    if delay > 0:
        delay -= 1
    '''
    if i>100:
        break
    '''

wallet.ViewBalance('KRW-BTC', price_current)
trend.to_excel("3m15c_b-d3u3_s-p05-l2.xlsx")
print('#end')
