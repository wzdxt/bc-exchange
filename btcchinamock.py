#!/usr/bin/python
# -*- coding: utf-8 -*-
 
from btcchina import BTCChina

class BTCChinaMock(BTCChina):
	def __init__(self, access, secret):
		BTCChina.__init__(self, access, secret)
		self.orders = []
		self.order_id = 1
		self.btc_amount = 0
		self.cny_amount = 0

	def get_orders(self):
		orders = BTCChina.get_market_depth(self, 1)['market_depth']
		bid_price = orders['bid'][0]['price']
		ask_price = orders['ask'][0]['price']
		i = 0
		while i < len(self.orders):
			order = self.orders[i]
			if order['type'] == 'bid':
				if ask_price <= order['price']:
					self.btc_amount = self.btc_amount + order['amount']
					self.cny_amount = self.cny_amount - order['price'] * order['amount']
					del self.orders[i]
					print 'buy success, last ask:', ask_price
				else:
					i = i + 1
			else:
				if bid_price >= order['price']:
					self.btc_amount = self.btc_amount - order['amount']
					self.cny_amount = self.cny_amount + order['price'] * order['amount']
					del self.orders[i]
					print 'sell success, last bid:', bid_price
				else:
					i = i + 1
		return {'order': self.orders}
	
	def buy(self, price, amount):
		new_order = {
			'id' : self.order_id,
			'price' : price,
			'amount' : amount,
			'type' : 'bid',
			}
		self.orders.append(new_order)
		self.order_id = self.order_id + 1
		return True;

	def sell(self, price, amount):
		new_order = {
			'id' : self.order_id,
			'price' : price,
			'amount' : amount,
			'type' : 'ask',
			}
		self.orders.append(new_order)
		self.order_id = self.order_id + 1
		return True;

	def get_account_info(self):
		return {'balance' : {
				'btc' : {'amount' : self.btc_amount},
				'cny' : {'amount' : self.cny_amount}
				}}

	def cancel(self, id):
		for i in range(0, len(self.orders)):
			if self.orders[i]['id'] == id:
				del self.orders[i]
				return True
		return False
