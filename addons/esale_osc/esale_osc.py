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
import xmlrpclib
from mx import DateTime

class esale_osc_web(osv.osv):
	_name = "esale_osc.web"
	_description = "OScommerce Website"
	_columns = {
		'name': fields.char('Name',size=64, required=True),
		'url': fields.char('URL', size=64, required=True),
		'shop_id': fields.many2one('sale.shop', 'Sale Shop', required=True),
		'partner_anonymous_id': fields.many2one('res.partner', 'Anonymous', required=True),
		'active': fields.boolean('Active'),
		'product_ids': fields.one2many('esale_osc.product', 'web_id', 'Web Products'),
		'language_ids': fields.one2many('esale_osc.lang', 'web_id', 'Languages'),
		'tax_ids': fields.one2many('esale_osc.tax', 'web_id', 'Taxes'),
		'category_ids': fields.one2many('esale_osc.category', 'web_id', 'Categories'),
	}
	_defaults = {
		'active': lambda *a: 1
	}

	def add_all_products(self, cr, uid, ids, *args):
		product_pool=self.pool.get('esale_osc.product')
		for id in ids:
			cr.execute("select p.id from product_product as p left join esale_osc_product as o on p.id=o.product_id and o.web_id=%d where o.id is NULL;" % id)
			for [product] in cr.fetchall():
				value={	'product_id'	: product,
						'web_id'		: id
					}
				value.update(product_pool.onchange_product_id(cr, uid, [], product, id)['value'])
				product_pool.create(cr, uid, value)
		return True

	def tax_import(self, cr, uid, ids, *args):
		for website in self.browse(cr, uid, ids):
			server = xmlrpclib.ServerProxy("%s/tinyerp-syncro.php" % website.url)
			taxes = server.get_taxes()
			for tax in taxes:
				value={
					'web_id'		: website.id,
					'esale_osc_id'	: tax[0],
					'name'		: tax[1]
				}
				self.pool.get('esale_osc.tax').create(cr, uid, value)
		return True

	def lang_import(self, cr, uid, ids, *args):
		for website in self.browse(cr, uid, ids):
			server = xmlrpclib.ServerProxy("%s/tinyerp-syncro.php" % website.url)
			languages = server.get_languages()
			for language in languages:
				value={	'web_id'		: website.id,
						'esale_osc_id'	: language[0],
						'name'		: language[1]
				}
				self.pool.get('esale_osc.lang').create(cr, uid, value)
		return True

	def category_import(self, cr, uid, ids, *args):
		for website in self.browse(cr, uid, ids):
			server = xmlrpclib.ServerProxy("%s/tinyerp-syncro.php" % website.url)
			categories = server.get_categories()
			category_pool = self.pool.get('esale_osc.category')
			for category in categories:
				value={	'web_id'		: website.id,
						'esale_osc_id'	: category[0],
						'name'		: category[1]
				}
				existing = category_pool.search(cr, uid, [('web_id','=',website.id), ('esale_osc_id', '=', category[0])])
				if len(existing)>0:
					category_pool.write(cr, uid, existing, value)
				else:
					category_pool.create(cr, uid, value)
		return True	

esale_osc_web()

class esale_osc_tax(osv.osv):
	_name = "esale_osc.tax"
	_description = "esale_osc Tax"
	_columns = {
		'name'		: fields.char('Tax name', size=32, required=True),
		'esale_osc_id'	: fields.integer('esale_osc ID'),
		'tax_id'		: fields.many2one('account.tax', 'Tax'),
		'web_id'		: fields.many2one('esale_osc.web', 'Website')
	}
esale_osc_tax()

class esale_osc_category(osv.osv):
	_name = "esale_osc.category"
	_description = "esale_osc Category"
	_columns = {	'name'		: fields.char('Name', size=64, reuired=True),
				'esale_osc_id'	: fields.integer('esale_osc ID', required=True),
				'web_id'		: fields.many2one('esale_osc.web', 'Website'),
				'category_id'	: fields.many2one('product.category', 'Category'),
				}
esale_osc_category()

class esale_osc_product(osv.osv):
	_name = "esale_osc.product"
	_description = "esale_osc Product"
	_columns = {	'web_id'			: fields.many2one('esale_osc.web', 'Web Ref'),
				'name'			: fields.char('Name', size=64, required=True),
				'product_id'		: fields.many2one('product.product', 'Product', required=True),
				'esale_osc_id'		: fields.integer('esale_osc product id'),
				'esale_osc_tax_id'	: fields.many2one('esale_osc.tax', 'esale_osc tax'),
				}

	def onchange_product_id(self, cr, uid, ids, product_id, web_id):
		value={}
		if (product_id):
			product=self.pool.get('product.product').browse(cr, uid, product_id)
			value['name']=product.name
		return {'value': value}
esale_osc_product()

class esale_osc_language(osv.osv):
	_name = "esale_osc.lang"
	_description = "esale_osc Language"
	_columns = {	'name'			: fields.char('Name', size=32, required=True),
					'esale_osc_id'	: fields.integer('esale_osc ID', required=True),
					'language_id'	: fields.many2one('res.lang', 'Language'),
					'web_id'		: fields.many2one('esale_osc.web', 'Website')
				}
esale_osc_language()

class esale_osc_saleorder(osv.osv):
	_inherit='sale.order'
	_name='sale.order'
	_table='sale_order'
	_columns = {
		'esale_osc_web': fields.many2one('esale_osc.web', 'Website'),
		'esale_osc_id': fields.integer('esale_osc Id'),
	}
	_defaults = {
		'esale_osc_id': lambda *a: False,
	}

	def onchange_esale_osc_web(self, cr, uid, ids, esale_osc_web):
		value={}
		if esale_osc_web:
			web=self.pool.get('esale_osc.web').browse(cr, uid, esale_osc_web)
			value['shop_id']=web.shop_id.id
			value['partner_id']=web.partner_anonymous_id.id
			value.update(self.pool.get('sale.order').onchange_shop_id(cr, uid, ids, value['shop_id'])['value'])
			value.update(self.pool.get('sale.order').onchange_partner_id(cr, uid, ids, value['partner_id'])['value'])

		return {'value':value}

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

esale_osc_saleorder()
