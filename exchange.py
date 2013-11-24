#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division
 
import time
import random
import urllib2
import json
import math
import copy

import btcchinamock
from key import *
 
MARKET_SIZE = 200

BUT_BTC_NUMBER = 0.1

# order
BUY_PRICE_C = 1.00001
SELL_PRICE_C = 1.001

# amount check
BID_CHECK_STEP_C = -0.0005
BID_AMOUNT_SLOPE = -7.333
BID_AMOUNT_FIX = -100
ASK_CHECK_STEP_C = 0.0005
ASK_AMOUNT_SLOPE = 7.333
ASK_AMOUNT_FIX = 100

OMIT_GAP_C = 0.001
PRICE_GAP_COMPARE_C = 0.01

# wave check
WAVE_SHRESHOLD_HORIZON_LIGHT = 100
WAVE_SHRESHOLD_LIGHT_NORMAL = 200
WAVE_SHRESHOLD_NORMAL_HEAVY = 400
WAVE_LEVEL_HORIZON = 1
WAVE_LEVEL_LIGHT = 2
WAVE_LEVEL_NORMAL = 3
WAVE_LEVEL_HEAVY = 4
WAVE_LEVEL_TERRIBLE = 5
LIGHT_PRICE_FIX_C = 0.999
NORMAL_PRICE_FIX_C = 1.001
HEAVY_PRICE_FIX_C = 1

RAISE_UP_C = 0.0006

STATUS_LOOK = 1
STATUS_START_BUY = 2
STATUS_BUYING = 3
STATUS_BUY_PART = 4
STATUS_BUY_FINISH = 5
STATUS_SELLING = 6

ticker_cache = {'pp':[], 't':0, 'tt':[]}
headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}

def run():

	status = STATUS_LOOK

	while True:
		bc = btcchinamock.BTCChinaMock(access_key,secret_key)

		try:
			while True:
				if (status == STATUS_LOOK):
					print
					# check network
					start_time = time.time()
					market_depth = bc.get_market_depth(MARKET_SIZE)['market_depth']
					end_time = time.time()
					if end_time - start_time > 2:
						print 'xxxxxxxxxxxx bad network xxxxxxxxxxxxxx'
						time.sleep(3)
						continue
					# check market
					print_cny(bc)
					price_check = check_price(market_depth) # order is important!
					depth_check = check_depth(market_depth) #
					print 'price check:', price_check, 'less is good'
					print 'depth check:', depth_check, 'larger is good'
					if (price_check[0] and depth_check[1] > 1) or(price_check[1]/depth_check[1]**2 < 0.0001):
						status = STATUS_START_BUY
					else:
						time.sleep(3)
				elif status == STATUS_START_BUY:
					print '*********** start buy *************'
					try:
						buy_price = market_depth['ask'][0]['price'] * BUY_PRICE_C
						bc.buy(buy_price, BUT_BTC_NUMBER);
						status = STATUS_BUYING
						print 'buy for', buy_price
					except:
						print 'xxxxxxxxxx buy error xxxxxxxxxxxxx'
				elif (status == STATUS_BUYING):
					cancel_order_if_not_deal(bc)
					(status, btc_amount) = get_status_after_buy(bc)
					if __debug__ and status == STATUS_BUY_FINISH:
						print '************* buy succeed **************'
				elif (status == STATUS_BUY_FINISH):
					while True:
						try:
							if bc.sell(buy_price * SELL_PRICE_C, btc_amount):
								print 'sell for', buy_price * SELL_PRICE_C
								break
						except Exception, e:
							print 'xxxxxxxxxxxxx sell error xxxxxxxxxxxxxx'
							print e
					status = STATUS_SELLING
				elif (status == STATUS_SELLING):
					status = get_status_after_sell(bc)
					if status == STATUS_LOOK:
						print '*************** sell succeed ***************'
						print_cny(bc)
					else:
						print 'xxxxxxxxxx continue selling xxxxxxxxxxx'
						time.sleep(3)
				else:
					raise Exception('status error')
		except Exception, e:
			print 'exception: ', e
			time.sleep(1)

def print_cny(bc):
	cny = bc.get_account_info()['balance']['cny']['amount']
	print 'cny =', cny

def get_status_after_sell(bc):
	if len(bc.get_orders()['order']) == 0:
		return STATUS_LOOK
	else:
		return STATUS_SELLING

def get_status_after_buy(bc):
	btc_amount = float(bc.get_account_info()['balance']['btc']['amount'])
	if btc_amount > 0:
		return (STATUS_BUY_FINISH, btc_amount)
	else:
		return (STATUS_LOOK, 0)

def cancel_order_if_not_deal(bc):
	while True:
		orders = bc.get_orders()['order']
		for order in orders:
			while True:
				try:
					bc.cancel(order['id'])
					if __debug__:
						print 'cancel order:', order['id']
					break
				except:
					print 'xxxxxxxxx cancel order fail xxxxxxxxx'
		if len(bc.get_orders()['order']) == 0:
			break

def check_depth(market_depth):
	return check_bid_and_ask2(market_depth)

def check_bid_and_ask(market_depth):
	bids = market_depth['bid']
	asks = market_depth['ask']
	first_price = asks[0]['price']
	if (not check_bid(first_price, bids)):
		return False
	if (not check_ask(first_price, asks)):
		return False
	return True

def check_bid_and_ask2(market_depth):
	bids = market_depth['bid']
	asks = market_depth['ask']
	# kick small orders
	if False:
		i = 0
		while i < len(bids):
			if bids[i]['amount'] < 0.1:
				del bids[i]
			else:
				i = i + 1
		i = 0
		while i < len(asks):
			if asks[i]['amount'] < 0.1:
				del asks[i]
			else:
				i = i + 1
	# compare amount
	ret = True
	evaluation = 0
	askp0 = asks[0]['price']
	bid_amount = 0;
	bid_price_gap = 0;
	bid_index = 1;
	ask_amount = 0;
	ask_price_gap = 0;
	ask_index = 1;
	while bid_index < len(bids) and bid_price_gap < askp0 * PRICE_GAP_COMPARE_C:
		bid_price_gap = askp0 - bids[bid_index]['price']
		bid_amount = bid_amount + bids[bid_index]['amount']
		bid_index = bid_index + 1;
		while ask_price_gap < bid_price_gap and ask_index < len(asks):
			ask_price_gap = asks[ask_index]['price'] - askp0
			ask_amount = ask_amount + asks[ask_index]['amount']
			ask_index = ask_index + 1
		c = 1.01 - 0.0002 * bid_index
		evaluation = evaluation + (bid_amount/bid_price_gap)/(ask_amount/ask_price_gap*c)
		if (bid_price_gap > askp0 * OMIT_GAP_C) and (bid_amount/bid_price_gap < ask_amount/ask_price_gap * c):
			if __debug__ and False:
				print 'market depth check fail:'
				print '','',bids[bid_index]['price'], bid_amount, bid_price_gap
				if ask_index < len(asks):
					print '','',asks[ask_index]['price'], ask_amount, ask_price_gap
				else:
					print '','',asks[ask_index-1]['price'], ask_amount, ask_price_gap
			ret = False;
		if ask_index >= len(asks):
			break
	return (ret, evaluation / bid_index)

def check_bid(first_price, bids):
	if __debug__:
		print 'check bid'
	price_step = BID_CHECK_STEP_C * bids[0]['price']
	amount_slope = BID_AMOUNT_SLOPE
	amount_fix = BID_AMOUNT_FIX
	return check_market_depth_amount(bids, first_price, price_step, amount_slope, amount_fix, 1)

def check_ask(first_price, asks):
	if __debug__:
		print 'check ask'
	price_step = ASK_CHECK_STEP_C * asks[0]['price']
	amount_slope = ASK_AMOUNT_SLOPE
	amount_fix = ASK_AMOUNT_FIX
	return check_market_depth_amount(asks, first_price, price_step, amount_slope, amount_fix, -1)

def check_market_depth_amount(orders, first_price, price_step, amount_slope, amount_fix, up):
	# kick small orders
	i = 0
	while i < len(orders):
		if orders[i]['amount'] < 0.1:
			del orders[i]
		else:
			i = i + 1
	#########################
	last_price = orders[-1]['price']
	step_time = (orders[-1]['price']-orders[0]['price'])//price_step + 1

	test_price = first_price
	shreshold_amount = amount_fix
	order_index = 0
	total_amount = 0
	while (test_price - last_price) * up > 0:
		while (orders[order_index]['price'] - test_price) * up > 0:
			total_amount = total_amount + orders[order_index]['amount']
			order_index = order_index + 1

		shreshold_amount = shreshold_amount + price_step * amount_slope
		if not ((total_amount - shreshold_amount) * up > 0):
			if __debug__:
				if up == 1:
					print 'fail: bid'
				else:
					print 'fail: ask'
				print 'test price:', test_price
				print 'total amount:', total_amount
				print 'shreshold amount:', shreshold_amount
			return False

		test_price = test_price + price_step
	return True

def check_price(market):
	url = "http://mm.btc123.com/data/getmmJSON.php?type=mmTicHis_btcchina_3600&s=" + str(random.random())
	ticker_hist = get_ticker_history(url)

	ave_price = get_ave_price(ticker_hist)
	wave_level = get_wave_level(ticker_hist, ave_price)
	raise_up = is_raise_up(ticker_hist, ave_price)
	last_price = market['ask'][0]['price']

	ret = True
	evaluation = 100000

	if not raise_up:
		if __debug__:
			print 'price check fail: not raise up'
		return (False, evaluation)

	if wave_level == WAVE_LEVEL_HORIZON:
		if __debug__:
			print 'price check fail: horizon wave'
		ret = False
	elif wave_level == WAVE_LEVEL_TERRIBLE:
		if __debug__:
			print 'price check fail: terrible wave'
		ret = False
	elif wave_level == WAVE_LEVEL_LIGHT:
		if last_price > ave_price * LIGHT_PRICE_FIX_C:
			if __debug__:
				print 'light wave price check fail: ', last_price, '>', ave_price, '*', LIGHT_PRICE_FIX_C
				print 'price evaluation value:', last_price / (ave_price * LIGHT_PRICE_FIX_C)
			ret = False
			evaluation = last_price / (ave_price * LIGHT_PRICE_FIX_C) - 1
	elif wave_level == WAVE_LEVEL_NORMAL:
		if last_price > ave_price * NORMAL_PRICE_FIX_C:
			if __debug__:
				print 'normal wave price check fail: ', last_price, '>', ave_price, '*', NORMAL_PRICE_FIX_C
				print 'price evaluation value:', last_price / (ave_price * NORMAL_PRICE_FIX_C)
			ret = False
			evaluation = last_price / (ave_price * NORMAL_PRICE_FIX_C) - 1
	elif wave_level == WAVE_LEVEL_HEAVY:
		if last_price > ave_price * HEAVY_PRICE_FIX_C:
			if __debug__:
				print 'heavy wave price check fail: ', last_price, '>', ave_price, '*', HEAVY_PRICE_FIX_C
				print 'price evaluation value:', last_price / (ave_price * HEAVY_PRICE_FIX_C)
			ret = False
			evaluation = last_price / (ave_price * HEAVY_PRICE_FIX_C) - 1
	return (ret, evaluation)

def get_ticker_history(url):
	req = urllib2.Request(url, headers=headers)
	content = urllib2.urlopen(req).read()
	ticker_hist = json.loads(content)

	global ticker_cache
	if ticker_cache['t'] == ticker_hist['t']:
		get_update_data(ticker_cache)
		ticker_hist = copy.deepcopy(ticker_cache)
	else:
		calc_time(ticker_hist)
		get_update_data(ticker_hist)
		ticker_cache = copy.deepcopy(ticker_hist)
	
	pp = ticker_hist['pp']
	t = ticker_hist['t']
	tt = ticker_hist['tt']
	size = len(pp)
	pp = pp[size//2 : ]
	t = tt[size//2 - 1]
	tt = tt[size//2 : ]
	ticker_hist['pp'] = pp
	ticker_hist['t'] = t
	ticker_hist['tt'] = tt

	return ticker_hist

def calc_time(ticker):
	t = ticker['t']
	tt = ticker['tt']
	tt[0] = t + tt[0]
	for i in range(1, len(tt)):
		tt[i] = tt[i] + tt[i-1]

def get_update_data(ticker):
	url = 'http://mm.btc123.com/data/getmmJSON.php?type=mmTicUpd_btcchina&s=' + str(random.random())
	req = urllib2.Request(url, headers = headers)
	content = urllib2.urlopen(req).read()
	new_ticker = json.loads(content)
	if ticker['tt'][-1] == new_ticker['timestamp']:
		ticker['pp'][-1] = new_ticker['last']
	elif ticker['tt'][-1] < new_ticker['timestamp']:
		ticker['pp'].append(new_ticker['last'])
		ticker['tt'].append(new_ticker['timestamp'])

def get_wave_level(ticker_hist, ave_price):
	pp = ticker_hist['pp']
	wave_point = 0
	for i in range(5, len(pp)):
		wave_point = wave_point + abs(pp[i] - pp[i-5]) / 5 / ave_price * i**2
	if wave_point > WAVE_SHRESHOLD_NORMAL_HEAVY:
		wave_level = WAVE_LEVEL_HEAVY
	elif wave_point > WAVE_SHRESHOLD_LIGHT_NORMAL:
		wave_level = WAVE_LEVEL_NORMAL
	elif wave_point > WAVE_SHRESHOLD_HORIZON_LIGHT:
		wave_level = WAVE_LEVEL_LIGHT
	else:
		wave_level = WAVE_LEVEL_HORIZON
	last_pp = pp[-30 : ]
	if __debug__:
		print 'check terrible:', max(last_pp), min(last_pp)
	if max(last_pp)-min(last_pp) > ave_price * 0.03:
		wave_levvel = WAVE_LEVEL_TERRIBLE
	if __debug__:
		print 'wave point:', wave_point
		print 'wave level:', wave_level
	return wave_level

def is_raise_up(ticker_hist, ave_price):
	pp = ticker_hist['pp']
	p1 = pp[-1]
	p2 = sum(pp[-6 : -1]) / 5
	ret = p1 - p2 > ave_price * RAISE_UP_C
	if not ret and __debug__:
		print 'not raise up:', p1, p2, ave_price * 0.0006
	return ret

def get_ave_price(ticker_hist):
	pp = ticker_hist['pp']
	count = 0
	for price in pp:
		count = count + price
	ret = count/len(pp)
	if __debug__:
		print 'ave price:', ret
	return ret

if __name__ == '__main__':
	run()
