# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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

import time
import netsvc
from osv import fields, osv
import ir

class sale_order(osv.osv):
	_inherit = "sale.order"
	def _amount_tax(self, cr, uid, ids, field_name, arg, context):
		res = {}
		cur_obj=self.pool.get('res.currency')
		for order in self.browse(cr, uid, ids):
			val = 0.0
			cur=order.pricelist_id.currency_id
			for line in order.order_line:
				if order.price_type=='tax_included':
					ttt = self.pool.get('account.tax').compute_inv(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0)/100.0), line.product_uom_qty, order.partner_invoice_id.id, line.product_id, order.partner_id)
				else:
					ttt = self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0)/100.0), line.product_uom_qty, order.partner_invoice_id.id, line.product_id, order.partner_id)
				for c in ttt:
					val += cur_obj.round(cr, uid, cur, c['amount'])
			res[order.id]=cur_obj.round(cr, uid, cur, val)
		return res
	_columns = {
		'price_type': fields.selection([
			('tax_included','Tax included'),
			('tax_excluded','Tax excluded')
		], 'Price method', required=True),
		'amount_tax': fields.function(_amount_tax, method=True, string='Taxes'),
	}
	_defaults = {
		'price_type': lambda *a: 'tax_excluded',
	}
	def _inv_get(self, cr, uid, order, context={}):
		return {
			'price_type': order.price_type
		}
sale_order()

class sale_order_line(osv.osv):
	_inherit = "sale.order.line"
	def _amount_line(self, cr, uid, ids, name, arg, context):
		res = {}
		cur_obj=self.pool.get('res.currency')
		tax_obj = self.pool.get('account.tax')
		res = super(sale_order_line, self)._amount_line(cr, uid, ids, name, arg, context)
		res2 = res.copy()
		for line in self.browse(cr, uid, ids):
			if line.product_uos.id:
				qty = line.product_uos_qty
			else:
				qty = line.product_uom_qty
			if line.order_id.price_type == 'tax_included':
				if line.product_id:
					for tax in tax_obj.compute_inv(cr, uid, line.product_id.taxes_id, res[line.id]/qty, qty):
						res[line.id] = res[line.id] - tax['amount']
				else:
					for tax in tax_obj.compute_inv(cr, uid, line.tax_id, res[line.id]/qty, qty):
						res[line.id] = res[line.id] - tax['amount']
			if name == 'price_subtotal_incl' and line.order_id.price_type == 'tax_included':
				if line.product_id:
					prod_taxe_ids = [ t.id for t in line.product_id.taxes_id ]
					prod_taxe_ids.sort()
					line_taxe_ids = [ t.id for t in line.tax_id ]
					line_taxe_ids.sort()
				if line.product_id and prod_taxe_ids == line_taxe_ids:
					res[line.id] = res2[line.id]
				elif not line.product_id:
					res[line.id] = res2[line.id]
				else:
					for tax in tax_obj.compute(cr, uid, line.tax_id, res[line.id]/qty, qty):
						res[line.id] = res[line.id] + tax['amount']
			cur = line.order_id.pricelist_id.currency_id
			res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
		return res
	_columns = {
		'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal w/o tax'),
		'price_subtotal_incl': fields.function(_amount_line, method=True, string='Subtotal'),
	}
sale_order_line()

