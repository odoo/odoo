##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: sale.py 1005 2005-07-25 08:41:42Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import netsvc
from osv import fields,osv,orm
import ir

import time
from mx import DateTime

class esale_web(osv.osv):
	_name = "esale.web"
	_description = "eCommerce Website"
	_columns = {
		'name': fields.char('eShop Name',size=64, required=True),
		'shop_id': fields.many2one('sale.shop', 'Sale Shop', required=True),
		'partner_anonymous_id': fields.many2one('res.partner', 'Anonymous', required=True),
		'active': fields.boolean('Active'),
		'product_all': fields.boolean('All product'),
		'product_ids': fields.many2many('product.product', 'esale_web_product_rel', 'web_id', 'product_id', 'Web Products')
	}
	_defaults = {
		'product_all': lambda *a: 1,
		'active': lambda *a: 1
	}
	#
	# Compute the stock for one product depending on the POS
	#
	def stock_get(self, cr, uid, shop_id, product_id):
		res = self.pool.get('product.product').read(cr, uid, [product_id], ['qty_available'], {'shop': shop_id})[0]['qty_available']
		return res

	#
	# Compute the price for one product
	#
	def price_get(self, cr, uid, product_id, product_qty, partner_id):
		pricelist = self.pool.get('res.partner').browse(cr, uid, partner_id).property_product_pricelist.id
		price = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist], product_id, product_qty)[pricelist]
		return price

	#
	# PRE:
	# order = {
	#    'partner_id': 1,
	#    'partner_name:'',
	#    'date':'20051010',
	#    'user_id':1,
	#    'products':[
	#         {'product_id':1,
	#          'product_name':'',
	#          'price':19.9, 
	#          'product_qty': 1}
	#    ]
	#
	# POST:
	# order.extend({'price_subtotal': 0.0,
	#  'price_tax': 0.0,
	#  'price_total': 0.0,
	#  'products': [
	#         {'product_id':1,
	#          'product_name':'',
	#          'price':19.9,
	#          'product_qty': 1,
	#          'qty_available': 1,
	#          'date_available': '20051010'}
	#  ]})
	#
	def compute(self, cr, uid, ids, order, context={}):
		pricelist = self.pool.get('res.partner').browse(cr, uid, order['partner_id']).property_product_pricelist.id
		subtotal = 0
		taxes = 0
		for product in order['products']:
			product_id = int(product['product_id'])
			price = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist], product_id, int(product['product_qty']))[pricelist]
			product['price'] = price

			prod_info = self.pool.get('product.product').read(cr, uid, [product_id], ['sale_delay', 'qty_available', 'code', 'name'])[0]
			dt = (DateTime.now() + DateTime.RelativeDateTime(days=prod_info['sale_delay'] or 0.0)).strftime('%Y-%m-%d')
			product['date_available'] = dt
			product['qty_available'] = prod_info['qty_available']
			product['code'] = prod_info['code']
			product['name'] = prod_info['name']
			product['subtotal'] = price * int(product['product_qty'])
			subtotal += (price * int(product['product_qty']))
			taxes += 0
		order['price_subtotal'] = subtotal
		order['price_tax'] = taxes
		order['price_total'] = taxes + subtotal
		return order
esale_web()

#
# Not yet Used !
# For futur development, used to stock web user preferences
#
class esale_user(osv.osv):
	_name = "esale.user"
	_description = "eCommerce User"
	_columns = {
		'name': fields.char('User Name',size=64, required=True),
		'partner_id':fields.many2one('res.partner','Partner',required=True),
		'picking_policy': fields.selection([
			('direct','Direct Delivery'),
			('one','All at once')
		], 'Packing Policy', required=True ),
		'order_policy': fields.selection([
			('prepaid','Pay before delivery'),
			('manual','Shipping & Manual Invoice'),
			('postpaid','Invoice after delivery'),
		], 'Shipping Policy', required=True),
		'web_ref':fields.char('Web Reference', size=16, required=True),
		'web_id': fields.many2one('esale.web', 'Web Shop', required=True),
	}
	_defaults = {
		'order_policy': lambda *a: 'prepaid',
		'picking_policy': lambda *a: 'one'
	}
esale_user()

class esale_order(osv.osv):
	_name='esale.order'
	_columns = {
		'name': fields.char('Order Description',size=64, required=True),
		'state': fields.selection([
			('draft','Draft'),
			('done','Done'),
			('cancel','Cancel')
		], 'Order State'),
		'date_order':fields.date('Date Ordered', required=True),
		'partner_id':fields.many2one('res.partner', 'Partner', required=True),
		'web_id':fields.many2one('esale.web', 'Web Shop', required=True),
		'web_ref':fields.integer('Web Ref'),
		'order_lines': fields.one2many('esale.order.line', 'order_id', 'Order Lines'),
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'note': fields.text('Notes'),
	}
	_defaults = {
		'date_order': lambda *a: time.strftime('%Y-%m-%d'),
		'state': lambda *a: 'draft',
	}

	def order_create(self, cr, uid, ids, context={}):
		for order in self.browse(cr, uid, ids, context):
			addr = self.pool.get('res.partner').address_get(cr, uid, [order.partner_id.id], ['delivery','invoice','contact'])
			pricelist_id=order.partner_id.property_product_pricelist.id
			order_lines = []
			for line in order.order_lines:
				order_lines.append( (0,0,{
					'name': line.name,
					'product_qty': line.product_qty,
					'date_planned': line.date_planned,
					'product_id': line.product_id.id,
					'product_uom': line.product_uom.id,
					'price_unit': line.price_unit,
					'type': line.product_id.procure_method
				 }) )
			order_id = self.pool.get('sale.order').create(cr, uid, {
				'name': order.name,
				'shop_id': order.web_id.shop_id.id,
				'origin': 'WEB:'+str(order.id),
				'date_order': order.date_order,
				'user_id': uid,
				'partner_id': order.partner_id.id,
				'partner_invoice_id':addr['invoice'],
				'partner_order_id':addr['contact'],
				'partner_shipping_id':addr['delivery'],
				'pricelist_id': pricelist_id,
				'order_line': order_lines
			})
			self.write(cr, uid, [order.id], {'state':'done', 'order_id': order_id})
			wf_service = netsvc.LocalService("workflow")
			wf_service.trg_validate(uid, 'sale.order', order_id, 'order_confirm', cr)
		return True

	def order_cancel(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'cancel'})
		return True

	def order_upload(self, cr, uid, web_id, orders):
		for order in orders:
			lines = []
			for prod in order['order_lines']:
				prod['product_uom'] = self.pool.get('product.product').browse(cr, uid, [prod['product_id']])[0].uom_id.id
				lines.append( (0,0, prod) )
			self.create(cr, uid, {
				'name': str(order['ref'])+': '+order['partner_name'],
				'partner_id': int(order['partner_id']),
				'web_id': int(web_id),
				'web_ref':  int(order['ref']),
				'note': order['notes'],
				'order_lines': lines
			})
		return True

	def state_get(self, cr, uid, refs):
		result = {}
		for r in refs:
			result[str(r)] = False
		ids = self.search(cr, uid, [('web_ref','in',map(int,refs))])
		for order in self.browse(cr, uid, ids):
			if order.order_id:
				result[str(order.web_ref)] = order.order_id.state
			else:
				result[str(order.web_ref)] = 'draft'
		return result
esale_order()

class esale_order_line(osv.osv):
	_name = 'esale.order.line'
	_description = 'eSale Order line'
	_columns = {
		'name': fields.char('Order Line', size=64, required=True),
		'order_id': fields.many2one('esale.order', 'eOrder Ref'),
		'product_qty': fields.float('Quantity', digits=(16,2), required=True),
		'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok','=',True)], change_default=True),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True),
		'price_unit': fields.float('Unit Price', required=True),
		'date_planned': fields.date('Scheduled date', required=True),
	}
	_defaults = {
		'date_planned': lambda *a: time.strftime('%Y-%m-%d'),
	}
esale_order_line()


