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

class account_invoice(osv.osv):
	def _amount_untaxed(self, cr, uid, ids, prop, unknow_none,unknow_dict):
		ti = []
		for inv in self.read(cr, uid, ids, ['price_type']):
			if inv['price_type']=='tax_included':
				ti.append(inv['id'])
		id_set=",".join(map(str,ids))
		cr.execute("SELECT s.id,COALESCE(SUM(l.price_unit*l.quantity*(100.0-l.discount))/100.0,0)::decimal(16,2) AS amount FROM account_invoice s LEFT OUTER JOIN account_invoice_line l ON (s.id=l.invoice_id) WHERE s.id IN ("+id_set+") GROUP BY s.id ")
		res=dict(cr.fetchall())
		if len(ti):
			tax = self._amount_tax(cr, uid, ti, prop, unknow_none,unknow_dict)
			for id in ti:
				res[id] = res[id] - tax.get(id,0.0)
		return res

	def _amount_total(self, cr, uid, ids, prop, unknow_none,unknow_dict):
		ti = []
		for inv in self.read(cr, uid, ids, ['price_type']):
			if inv['price_type']=='tax_excluded':
				ti.append(inv['id'])
		id_set=",".join(map(str,ids))
		cr.execute("SELECT s.id,COALESCE(SUM(l.price_unit*l.quantity*(100.0-l.discount))/100.0,0)::decimal(16,2) AS amount FROM account_invoice s LEFT OUTER JOIN account_invoice_line l ON (s.id=l.invoice_id) WHERE s.id IN ("+id_set+") GROUP BY s.id ")
		res=dict(cr.fetchall())
		if len(ti):
			tax = self._amount_tax(cr, uid, ti, prop, unknow_none,unknow_dict)
			for id in ti:
				res[id] = res[id] + tax.get(id,0.0)
		return res

	_inherit = "account.invoice"
	_columns = {
		'price_type': fields.selection([
			('tax_included','Tax included'),
			('tax_excluded','Tax excluded')
		], 'Price method', required=True),
		'amount_untaxed': fields.function(_amount_untaxed, method=True, string='Untaxed Amount'),
		'amount_total': fields.function(_amount_total, method=True, string='Total'),
	}
	_defaults = {
		'price_type': lambda *a: 'tax_excluded',
	}
account_invoice()

class account_invoice_line(osv.osv):
	_inherit = "account.invoice.line"

	#
	# Compute with VAT invluded in the price
	#
	def move_line_get(self, cr, uid, invoice_id, context={}):
		inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id)
		if inv.price_type=='tax_excluded':
			return super(account_invoice_line,self).move_line_get(cr, uid, invoice_id)

		res = []
		tax_grouped = {}
		tax_obj = self.pool.get('account.tax')
		cur_obj = self.pool.get('res.currency')
		ait_obj = self.pool.get('account.invoice.tax')
		cur = inv.currency_id

		for line in inv.invoice_line:
			res.append( {
				'type':'src', 
				'name':line.name, 
				'price_unit':line.price_unit, 
				'quantity':line.quantity, 
				'price':cur_obj.round(cr, uid, cur, line.quantity*line.price_unit * (1.0- (line.discount or 0.0)/100.0)),
				'account_id':line.account_id.id,
			})
			for tax in tax_obj.compute_inv(cr, uid, line.invoice_line_tax_id, (line.price_unit *(1.0-(line['discount'] or 0.0)/100.0)), line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id):
				val={}
				val['invoice_id'] = inv.id
				val['name'] = tax['name']
				val['amount'] = cur_obj.round(cr, uid, cur, tax['amount'])
				val['manual'] = False
				val['sequence'] = tax['sequence']
				val['base'] = tax['price_unit'] * line['quantity']

				#
				# Setting the tax account and amount for the line
				#
				if inv.type in ('out_invoice','in_invoice'):
					val['base_code_id'] = tax['base_code_id']
					val['tax_code_id'] = tax['tax_code_id']
					val['base_amount'] = val['base'] * tax['base_sign']
					val['tax_amount'] = val['amount'] * tax['tax_sign']
					val['account_id'] = tax['account_collected_id'] or line.account_id.id
				else:
					val['base_code_id'] = tax['ref_base_code_id']
					val['tax_code_id'] = tax['ref_tax_code_id']
					val['base_amount'] = val['base'] * tax['ref_base_sign']
					val['tax_amount'] = val['amount'] * tax['ref_tax_sign']
					val['account_id'] = tax['account_paid_id'] or line.account_id.id

				res[-1]['tax_code_id'] = val['base_code_id']
				res[-1]['tax_amount'] = val['base_amount']

				key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
				if not key in tax_grouped:
					tax_grouped[key] = val
				else:
					tax_grouped[key]['amount'] += val['amount']
					tax_grouped[key]['base'] += val['base']
					tax_grouped[key]['base_amount'] += val['base_amount']
					tax_grouped[key]['tax_amount'] += val['tax_amount']
		# delete automatic tax lines for this invoice
		cr.execute("DELETE FROM account_invoice_tax WHERE NOT manual AND invoice_id=%d", (invoice_id,))
		for t in tax_grouped.values():
			ait_obj.create(cr, uid, t)
		return res
account_invoice_line()
