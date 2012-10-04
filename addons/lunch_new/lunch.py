# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import addons
import tools
import pytz
from osv import osv, fields

class lunch_order(osv.Model):
	""" lunch order """
	_name = 'lunch.order'
	_description = 'Lunch Order'

	def _price_get(self,cr,uid,ids,name,arg,context=None):
		orders = self.browse(cr,uid,ids,context=context)
		result={}
		for order in orders:
			value = 0.0
			for product in order.products:
				if product.state != 'cancelled':
					value+=product.product.price
					result[order.id]=value
		return result

	def _alerts_get(self,cr,uid,ids,name,arg,context=None):
		orders = self.browse(cr,uid,ids,context=context)
		alert_ref = self.pool.get('lunch.alert')
		alert_ids = alert_ref.search(cr,uid,[],context=context)
		result={}
		alert_msg= self._default_alerts_get(cr,uid,arg,context)
		for order in orders:
			if order.state=='new':
				result[order.id]=alert_msg
		return result

	def _default_alerts_get(self,cr,uid,arg,context=None):
		alert_ref = self.pool.get('lunch.alert')
		alert_ids = alert_ref.search(cr,uid,[],context=context)
		alert_msg=""
		for alert in alert_ref.browse(cr,uid,alert_ids,context=context):
			if alert :
				#there are alerts
				if alert.active==True:
					#the alert is active
					if alert.day=='specific':
						#the alert is only activated a specific day
						if alert.specific==fields.datetime.now().split(' ')[0]:
							print alert.specific
					elif alert.day=='week':
						#the alert is activated during some days of the week
						continue
					elif alert.day=='days':
						#the alert is activated everyday
						if alert.active_from==alert.active_to:
							#the alert is executing all the day
							alert_msg+=" * "
							alert_msg+=alert.message
							alert_msg+='\n'
						elif alert.active_from<alert.active_to:
							#the alert is executing from ... to ...
							now = fields.datetime.now().split(' ')[1]
							user = self.pool.get('res.users').browse(cr, uid, uid)
            				tz = pytz.timezone(user.tz) if user.tz else pytz.utc
            				hour_to = int(alert.active_to)
            				min_to = int((alert.active_to-hour_to)*60)
            				to_alert = ""+str(hour_to)+":"+str(min_to)
            				hour_from = int(alert.active_from)
            				min_from = int((alert.active_from-hour_from)*60)
            				from_alert = ""+str(hour_from)+":"+str(min_from)
            				if now>=from_alert and now<=to_alert:
								alert_msg+=" * "
								alert_msg+=alert.message
								alert_msg+='\n'
		return alert_msg

	def onchange_price(self,cr,uid,ids,products,context=None):
		res = {'value':{'total':0.0}}
		if products:
			tot = 0.0
			for prod in products:
				#price = self.pool.get('lunch.product').read(cr, uid, prod, ['price'])['price']
				#tot += price
				res = {'value':{'total':2.0}}
		#	prods = self.pool.get('lunch.order.line').read(cr,uid,products,['price'])['price']
		#	res = {'value':{'total': self._price_get(cr,uid,ids,products,context),}}
		return res

	_columns = {
		'user_id' : fields.many2one('res.users','User Name',required=True,readonly=True, states={'new':[('readonly', False)]}),
		'date': fields.date('Date', required=True,readonly=True, states={'new':[('readonly', False)]}),
		'products' : fields.one2many('lunch.order.line','order_id','Products',ondelete="cascade",readonly=True,states={'new':[('readonly', False)]}),
		'total' : fields.function(_price_get, string="Total",store=True),
		'state': fields.selection([('new', 'New'),('confirmed','Confirmed'), ('cancelled','Cancelled'), ('partially','Parcially Confirmed')], \
        	'Status', readonly=True, select=True),
		'alerts': fields.function(_alerts_get, string="Alerts", type='text'),
	}

	_defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': lambda self, cr, uid, context: 'new',
        'alerts': _default_alerts_get,
    }

class lunch_order_line(osv.Model): #define each product that will be in one ORDER.
	""" lunch order line """
	_name = 'lunch.order.line'
	_description = 'lunch order line'

	def _price_get(self,cr,uid,ids,name,arg,context=None):
		orderLines = self.browse(cr,uid,ids,context=context)
		result={}
		for orderLine in orderLines:
			result[orderLine.id]=orderLine.product.price
		return result

	def onchange_price(self,cr,uid,ids,product,context=None):
		if product:
			price = self.pool.get('lunch.product').read(cr, uid, product, ['price'])['price']
        	return {'value': {'price': price}}
		return {'value': {'price': 0.0}} 


	def confirm(self,cr,uid,ids,context=None):
		#confirm one or more order.line, update order status and create new cashmove
		cashmove_ref = self.pool.get('lunch.cashmove')
		orders_ref = self.pool.get('lunch.order')

		for order in self.browse(cr,uid,ids,context=context):
			if order.state!='confirmed':
				new_id = cashmove_ref.create(cr,uid,{'user_id': order.user_id.id, 'amount':0 - order.price,'description':order.product.name, 'order_id':order.id, 'state':'order', 'date':order.date})
				self.write(cr,uid,[order.id],{'cashmove':[('0',new_id)], 'state':'confirmed'},context)
		for order in self.browse(cr,uid,ids,context=context):
			isconfirmed = True
			for product in order.order_id.products:
				if product.state == 'new':
					isconfirmed = False
				if product.state == 'cancelled':
					isconfirmed = False
					orders_ref.write(cr,uid,[order.order_id.id],{'state':'partially'},context)
			if isconfirmed == True:
				orders_ref.write(cr,uid,[order.order_id.id],{'state':'confirmed'},context)
		return {}

	def cancel(self,cr,uid,ids,context=None):
		#confirm one or more order.line, update order status and create new cashmove
		cashmove_ref = self.pool.get('lunch.cashmove')
		orders_ref = self.pool.get('lunch.order')

		for order in self.browse(cr,uid,ids,context=context):
			self.write(cr,uid,[order.id],{'state':'cancelled'},context)
			for cash in order.cashmove:
				cashmove_ref.unlink(cr,uid,cash.id,context)
		for order in self.browse(cr,uid,ids,context=context):
			hasconfirmed = False
			hasnew = False
			for product in order.order_id.products:
				if product.state=='confirmed':
					hasconfirmed= True
				if product.state=='new':
					hasnew= True
			if hasnew == False:
				if hasconfirmed == False:
					orders_ref.write(cr,uid,[order.order_id.id],{'state':'cancelled'},context)
					return {}
			orders_ref.write(cr,uid,[order.order_id.id],{'state':'partially'},context)
		return {}

	_columns = {
		'date' : fields.related('order_id','date',type='date', string="Date", readonly=True,store=True),
		'supplier' : fields.related('product','supplier',type='many2one',relation='res.partner',string="Supplier",readonly=True,store=True),
		'user_id' : fields.related('order_id', 'user_id', type='many2one', relation='res.users', string='User', readonly=True),
		'product' : fields.many2one('lunch.product','Product',required=True), #one offer can have more than one product and one product can be in more than one offer.
		'note' : fields.text('Note',size=256,required=False),
		'order_id' : fields.many2one('lunch.order','Order',required=True,ondelete='cascade'),
		'price' : fields.function(_price_get, string="Price",store=True),
		'state': fields.selection([('new', 'New'),('confirmed','Confirmed'), ('cancelled','Cancelled')], \
        	'Status', readonly=True, select=True),
		'cashmove': fields.one2many('lunch.cashmove','order_id','Cash Move',ondelete='cascade'),
	}
	_defaults = {
		'state': lambda self, cr, uid, context: 'new',
    }

class lunch_product(osv.Model):
	""" lunch product """
	_name = 'lunch.product'
	_description = 'lunch product'
	_columns = {
		'name' : fields.char('Product',required=True, size=64),
		'category_id': fields.many2one('lunch.product.category', 'Category'),
		'description': fields.text('Description', size=256, required=False),
        'price': fields.float('Price', digits=(16,2)),
        'active': fields.boolean('Active'), #If this product isn't offered anymore, the active boolean is set to false. This will allow to keep trace of previous orders and cashmoves.
        'supplier' : fields.many2one('res.partner','Supplier',required=True, domain=[('supplier_lunch','=',True)]), 
	}

class lunch_product_category(osv.Model):
	""" lunch product category """
	_name = 'lunch.product.category'
	_description = 'lunch product category'
	_columns = {
		'name' : fields.char('Category', required=True, size=64), #such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...
	}

class lunch_cashmove(osv.Model):
	""" lunch cashmove => order or payment """
	_name = 'lunch.cashmove'
	_description = 'lunch description'
	_columns = {
		'user_id' : fields.many2one('res.users','User Name',required=True),
		'date' : fields.date('Date', required=True),
		'amount' : fields.float('Amount', required=True), #depending on the kind of cashmove, the amount will be positive or negative
		'description' : fields.text('Description',size=256), #the description can be an order or a payment
		'order_id' : fields.many2one('lunch.order.line','Order',required=False,ondelete='cascade'),
		'state' : fields.selection([('order','Order'),('payment','Payment')],'Is an order or a Payment'),
	}
	_defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'date': fields.date.context_today,
        'state': lambda self, cr, uid, context: 'payment',
    }


class lunch_alert(osv.Model):
	""" lunch alert """
	_name = 'lunch.alert'
	_description = 'lunch alert'
	_columns = {
		'message' : fields.text('Message',size=256, required=True),
		'active' : fields.boolean('Active'),
		'day' : fields.selection([('specific','Specific day'), ('week','Every Week'), ('days','Every Day')], 'Recurrency'),
		'specific' : fields.date('Day'),
		'monday' : fields.boolean('Monday'),
		'tuesday' : fields.boolean('Tuesday'),
		'wednesday' : fields.boolean('Wednesday'),
		'thursday' : fields.boolean('Thursday'),
		'friday' : fields.boolean('Friday'),
		'saturday' : fields.boolean('Saturday'),
		'sunday' :  fields.boolean('Sunday'),
		'active_from': fields.float('Between',required=True),
		'active_to': fields.float('And',required=True),
		#'active_from' : fields.selection([('0','00h00'),('1','00h30'),('2','01h00'),('3','01h30'),('4','02h00'),('5','02h30'),('6','03h00'),('7','03h30'),('8','04h00'),('9','04h30'),('10','05h00'),('11','05h30'),('12','06h00'),('13','06h30'),('14','07h00'),('15','07h30'),('16','08h00'),('17','08h30'),('18','09h00'),('19','09h30'),('20','10h00'),('21','10h30'),('22','11h00'),('23','11h30'),('24','12h00'),('25','12h30'),('26','13h00'),('27','13h30'),('28','14h00'),('29','14h30'),('30','15h00'),('31','15h30'),('32','16h00'),('33','16h30'),('34','17h00'),('35','17h30'),('36','18h00'),('37','18h30'),('38','19h00'),('39','19h30'),('40','20h00'),('41','20h30'),('42','21h00'),('43','21h30'),('44','22h00'),('45','22h30'),('46','23h00'),('47','23h30')],'Between',required=True), #defines from when (hours) the alert will be displayed
		#'active_to' : fields.selection([('0','00h00'),('1','00h30'),('2','01h00'),('3','01h30'),('4','02h00'),('5','02h30'),('6','03h00'),('7','03h30'),('8','04h00'),('9','04h30'),('10','05h00'),('11','05h30'),('12','06h00'),('13','06h30'),('14','07h00'),('15','07h30'),('16','08h00'),('17','08h30'),('18','09h00'),('19','09h30'),('20','10h00'),('21','10h30'),('22','11h00'),('23','11h30'),('24','12h00'),('25','12h30'),('26','13h00'),('27','13h30'),('28','14h00'),('29','14h30'),('30','15h00'),('31','15h30'),('32','16h00'),('33','16h30'),('34','17h00'),('35','17h30'),('36','18h00'),('37','18h30'),('38','19h00'),('39','19h30'),('40','20h00'),('41','20h30'),('42','21h00'),('43','21h30'),('44','22h00'),('45','22h30'),('46','23h00'),('47','23h30')],'and',required=True), # to when (hours) the alert will be disabled
	}


