# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

from osv import fields, osv

#from tools.misc import currency
from _common import rounding
import time
from tools import config

class price_type(osv.osv):
	"""
		The price type is used to points which field in the product form
		is a price and in which currency is this price expressed.
		When a field is a price, you can use it in pricelists to base
		sale and purchase prices based on some fields of the product.
	"""
	def _price_field_get(self, cr, uid, context={}):
		cr.execute('select name, field_description from ir_model_fields where model in (%s,%s) and ttype=%s order by name', ('product.product', 'product.template', 'float'))
		return cr.fetchall()
	def _get_currency(self, cr, uid, ctx):
		comp = self.pool.get('res.users').browse(cr,uid,uid).company_id
		if not comp:
			comp_id = self.pool.get('res.company').search(cr, uid, [])[0]
			comp = self.pool.get('res.company').browse(cr, uid, comp_id)
		return comp.currency_id.id

	_name = "product.price.type"
	_description = "Price type"
	_columns = {
		"name" : fields.char("Price Name", size=32, required=True, translate=True) ,
		"active" : fields.boolean("Active"),
		"field" : fields.selection(_price_field_get, "Product Field", required=True),
		"currency_id" : fields.many2one('res.currency', "Currency", required=True),
	}
	_defaults = {
		"active": lambda *args: True,
		"currency_id": _get_currency
	}
price_type()

#----------------------------------------------------------
# Price lists
#----------------------------------------------------------

class product_pricelist_type(osv.osv):
	_name = "product.pricelist.type"
	_description = "Pricelist Type"
	_columns = {
		'name': fields.char('Name',size=64, required=True),
		'key': fields.char('Key', size=64, required=True),
	}
product_pricelist_type()


class product_pricelist(osv.osv):
	def _pricelist_type_get(self, cr, uid, context={}):
		cr.execute('select key,name from product_pricelist_type order by name')
		return cr.fetchall()
	_name = "product.pricelist"
	_description = "Pricelist"
	_columns = {
		'name': fields.char('Name',size=64, required=True),
		'active': fields.boolean('Active'),
		'type': fields.selection(_pricelist_type_get, 'Pricelist Type', required=True),
		'version_id': fields.one2many('product.pricelist.version', 'pricelist_id', 'Pricelist Versions'),
		'currency_id': fields.many2one('res.currency', 'Currency', required=True),
	}
	def _get_currency(self, cr, uid, ctx):
		comp = self.pool.get('res.users').browse(cr,uid,uid).company_id
		if not comp:
			comp_id = self.pool.get('res.company').search(cr, uid, [])[0]
			comp = self.pool.get('res.company').browse(cr, uid, comp_id)
		return comp.currency_id.id

	_defaults = {
		'active': lambda *a: 1,
		"currency_id": _get_currency
	}

	def price_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
		'''
		context = {
			'uom': Unit of Measure (int),
			'partner': Partner ID (int),
			'date': Date of the pricelist (%Y-%m-%d),
		}
		'''
		context = context or {}
		currency_obj = self.pool.get('res.currency')
		product_obj = self.pool.get('product.product')
		supplierinfo_obj = self.pool.get('product.supplierinfo')
		price_type_obj = self.pool.get('product.price.type')

		if context and ('partner_id' in context):
			partner = context['partner_id']
		date = time.strftime('%Y-%m-%d')
		if context and ('date' in context):
			date = context['date']
		result = {}
		for id in ids:
			cr.execute('SELECT * ' \
					'FROM product_pricelist_version ' \
					'WHERE pricelist_id = %d AND active=True ' \
						'AND (date_start IS NULL OR date_start <= %s) ' \
						'AND (date_end IS NULL OR date_end >= %s) ' \
					'ORDER BY id LIMIT 1', (id, date, date))
			plversion = cr.dictfetchone()

			if not plversion:
				raise osv.except_osv('Warning !',
						'No active version for the selected pricelist !\n' \
								'Please create or activate one.')

			cr.execute('SELECT id, categ_id ' \
					'FROM product_template ' \
					'WHERE id = (SELECT product_tmpl_id ' \
						'FROM product_product ' \
						'WHERE id = %d)', (prod_id,))
			tmpl_id, categ = cr.fetchone()
			categ_ids = []
			while categ:
				categ_ids.append(str(categ))
				cr.execute('SELECT parent_id ' \
						'FROM product_category ' \
						'WHERE id = %d', (categ,))
				categ = cr.fetchone()[0]
				if str(categ) in categ_ids:
					raise osv.except_osv('Warning !',
							'Could not resolve product category, ' \
									'you have defined cyclic categories ' \
									'of products!')
			if categ_ids:
				categ_where = '(categ_id IN (' + ','.join(categ_ids) + '))'
			else:
				categ_where = '(categ_id IS NULL)'

			cr.execute(
				'SELECT i.*, pl.currency_id '
				'FROM product_pricelist_item AS i, '
					'product_pricelist_version AS v, product_pricelist AS pl '
				'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = %d) '
					'AND (product_id IS NULL OR product_id = %d) '
					'AND (' + categ_where + ' OR (categ_id IS NULL)) '
					'AND price_version_id = %d '
					'AND (min_quantity IS NULL OR min_quantity <= %f) '
					'AND i.price_version_id = v.id AND v.pricelist_id = pl.id '
				'ORDER BY sequence LIMIT 1',
				(tmpl_id, prod_id, plversion['id'], qty))
			res = cr.dictfetchone()
			if res:
				if res['base'] == -1:
					if not res['base_pricelist_id']:
						price = 0.0
					else:
						price_tmp = self.price_get(cr, uid,
								[res['base_pricelist_id']], prod_id,
								qty)[res['base_pricelist_id']]
						ptype_src = self.browse(cr, uid,
								res['base_pricelist_id']).currency_id.id
						price = currency_obj.compute(cr, uid, ptype_src,
								res['currency_id'], price_tmp, round=False)
				elif res['base'] == -2:
					where = []
					if partner:
						where = [('name', '=', partner) ] 
					sinfo = supplierinfo_obj.search(cr, uid,
							[('product_id', '=', tmpl_id)] + where)
					price = 0.0
					if sinfo:
						cr.execute('SELECT * ' \
								'FROM pricelist_partnerinfo ' \
								'WHERE suppinfo_id IN (' + \
									','.join(map(str, sinfo)) + ') ' \
									'AND min_quantity <= %f ' \
								'ORDER BY min_quantity DESC LIMIT 1', (qty,))
						res2 = cr.dictfetchone()
						if res2:
							price = res2['price']
				else:
					price_type = price_type_obj.browse(cr, uid, int(res['base']))
					price = currency_obj.compute(cr, uid,
							price_type.currency_id.id, res['currency_id'],
							product_obj.price_get(cr, uid, [prod_id],
								price_type.field, context)[prod_id], round=False)

				price_limit = price

				price = price * (1.0-(res['price_discount'] or 0.0))
				price = rounding(price, res['price_round'])
				price += (res['price_surcharge'] or 0.0)
				if res['price_min_margin']:
					price = max(price, price_limit+res['price_min_margin'])
				if res['price_max_margin']:
					price = min(price, price_limit+res['price_max_margin'])
			else:
				# False means no valid line found ! But we may not raise an
				# exception here because it breaks the search
				price = False
			result[id] = price
			if context and ('uom' in context):
				product = product_obj.browse(cr, uid, prod_id)
				uom = product.uos_id or product.uom_id
				result[id] = self.pool.get('product.uom')._compute_price(cr,
						uid, uom.id, result[id], context['uom'])
		return result

product_pricelist()


class product_pricelist_version(osv.osv):
	_name = "product.pricelist.version"
	_description = "Pricelist Version"
	_columns = {
		'pricelist_id': fields.many2one('product.pricelist', 'Price List',
			required=True, select=True),
		'name': fields.char('Name', size=64, required=True),
		'active': fields.boolean('Active'),
		'items_id': fields.one2many('product.pricelist.item',
			'price_version_id', 'Price List Items', required=True),
		'date_start': fields.date('Start Date'),
		'date_end': fields.date('End Date'),
	}
	_defaults = {
		'active': lambda *a: 1,
	}

	#
	# TODO: improve this function ?
	#
	def _check_date(self, cursor, user, ids):
		for pricelist_version in self.browse(cursor, user, ids):
			if not pricelist_version.active:
				continue
			cursor.execute('SELECT id ' \
					'FROM product_pricelist_version ' \
					'WHERE ((date_start <= %s AND %s <= date_end ' \
							'AND date_end IS NOT NULL) ' \
						'OR (date_end IS NULL AND date_start IS NOT NULL ' \
							'AND date_start <= %s) ' \
						'OR (date_start IS NULL AND date_end IS NOT NULL ' \
							'AND %s <= date_end) ' \
						'OR (date_start IS NULL AND date_end IS NULL) ' \
						'OR (%s = \'0000-01-01\' AND date_start IS NULL) ' \
						'OR (%s = \'0000-01-01\' AND date_end IS NULL) ' \
						'OR (%s = \'0000-01-01\' AND %s = \'0000-01-01\') ' \
						'OR (%s = \'0000-01-01\' AND date_start <= %s) ' \
						'OR (%s = \'0000-01-01\' AND %s <= date_end)) ' \
						'AND pricelist_id = %d ' \
						'AND active ' \
						'AND id <> %d', (pricelist_version.date_end or '0000-01-01',
							pricelist_version.date_start or '0000-01-01',
							pricelist_version.date_end or '0000-01-01',
							pricelist_version.date_start or '0000-01-01',
							pricelist_version.date_start or '0000-01-01',
							pricelist_version.date_end or '0000-01-01',
							pricelist_version.date_start or '0000-01-01',
							pricelist_version.date_end or '0000-01-01',
							pricelist_version.date_start or '0000-01-01',
							pricelist_version.date_end or '0000-01-01',
							pricelist_version.date_end or '0000-01-01',
							pricelist_version.date_start or '0000-01-01',
							pricelist_version.pricelist_id.id,
							pricelist_version.id))
			if cursor.fetchall():
				return False
		return True

	_constraints = [
		(_check_date, 'You can not have 2 pricelist version that overlaps!',
			['date_start', 'date_end'])
	]

product_pricelist_version()

class product_pricelist_item(osv.osv):
	def _price_field_get(self, cr, uid, context={}):
		cr.execute('select id,name from product_price_type where active')
		result = cr.fetchall()
		result.append((-1,'Other Pricelist'))
		result.append((-2,'Partner section of the product form'))
		return result

	_name = "product.pricelist.item"
	_description = "Pricelist item"
	_order = "sequence, min_quantity desc"
	_defaults = {
		'base': lambda *a: -1,
		'min_quantity': lambda *a: 0,
		'sequence': lambda *a: 5,
		'price_discount': lambda *a: 0,
	}
	_columns = {
		'name': fields.char('Name', size=64),
		'price_version_id': fields.many2one('product.pricelist.version', 'Price List Version', required=True, select=True),
		'product_tmpl_id': fields.many2one('product.template', 'Product Template'),
		'product_id': fields.many2one('product.product', 'Product'),
		'categ_id': fields.many2one('product.category', 'Product Category'),

		'min_quantity': fields.integer('Min. Quantity', required=True),
		'sequence': fields.integer('Sequence', required=True),
		'base': fields.selection(_price_field_get, 'Based on', required=True, size=-1),
		'base_pricelist_id': fields.many2one('product.pricelist', 'If Other Pricelist'),

		'price_surcharge': fields.float('Price Surcharge',
			digits=(16, int(config['price_accuracy']))),
		'price_discount': fields.float('Price Discount', digits=(16,4)),
		'price_round': fields.float('Price Rounding',
			digits=(16, int(config['price_accuracy']))),
		'price_min_margin': fields.float('Price Min. Margin',
			digits=(16, int(config['price_accuracy']))),
		'price_max_margin': fields.float('Price Max. Margin',
			digits=(16, int(config['price_accuracy']))),
	}
	def product_id_change(self, cr, uid, ids, product_id, context={}):
		if not product_id:
			return {}
		prod = self.pool.get('product.product').read(cr, uid, [product_id], ['code','name'])
		if prod[0]['code']:
			return {'value': {'name': prod[0]['code']}}
		return {}
product_pricelist_item()


