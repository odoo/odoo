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
		res = {}
		for invoice in self.browse(cr,uid,ids):
			res[invoice.id]= reduce( lambda x, y: x+y.price_subtotal,
									invoice.invoice_line,0)
		return res

	def _amount_total(self, cr, uid, ids, prop, unknow_none,unknow_dict):
		res = {}
		for invoice in self.browse(cr,uid,ids):
			res[invoice.id]= reduce( lambda x, y: x+y.price_subtotal_incl,
									invoice.invoice_line,0)
		return res

	def _amount_tax(self, cr, uid, ids, prop, unknow_none,unknow_dict):
		res = {}
		for invoice in self.browse(cr,uid,ids):
			res[invoice.id]= reduce( lambda x, y: x+y.amount,
									invoice.tax_line,0)
		return res

	_inherit = "account.invoice"
	_columns = {
		'price_type': fields.selection([('tax_included','Tax included'),
										('tax_excluded','Tax excluded')],
									   'Price method', required=True, readonly=True,
									   states={'draft':[('readonly',False)]}),
		'amount_untaxed': fields.function(_amount_untaxed, digits=(16,2), method=True,string='Untaxed Amount'),
		'amount_tax': fields.function(_amount_tax, method=True, string='Tax'),
		'amount_total': fields.function(_amount_total, method=True, string='Total'),
	}
	_defaults = {
		'price_type': lambda *a: 'tax_excluded',
	}
account_invoice()

class account_invoice_line(osv.osv):
	_inherit = "account.invoice.line"
	def _amount_line(self, cr, uid, ids, prop, unknow_none,unknow_dict):
		"""
		Return the subtotal excluding taxes with respect to price_type.
		"""
		#cur_obj = self.pool.get('res.currency')
		cur = False
		res = {}
		tax_obj = self.pool.get('account.tax')
		for line in self.browse(cr, uid, ids):
			res[line.id] = line.price_unit * line.quantity * (1-(line.discount or 0.0)/100.0)
		
			if line.product_id and line.invoice_id.price_type == 'tax_included':
				taxes = tax_obj.compute_inv(cr, uid,line.product_id.taxes_id,
											res[line.id],
											line.quantity)
				amount = 0
				for t in taxes : amount = amount + t['amount']
				cur = cur or line.invoice_id.currency_id
				res[line.id]= cur.round(cr, uid, cur, res[line.id] - amount) 
		return res

	def _amount_line_incl(self, cr, uid, ids, prop, unknow_none,unknow_dict):
		"""
		Return the subtotal including taxes with respect to price_type.
		"""
		res = {}
		cur = False
		tax_obj = self.pool.get('account.tax')
		for line in self.browse(cr, uid, ids):
			res[line.id] = line.price_unit * line.quantity * (1-(line.discount or 0.0)/100.0)
			if line.product_id:
				prod_taxe_ids = line.product_id and [t.id for t in line.product_id.taxes_id ] or []
				prod_taxe_ids.sort()
				line_taxe_ids = [ t.id for t in line.invoice_line_tax_id if t]
				line_taxe_ids.sort()
				if prod_taxe_ids == line_taxe_ids :
					continue
			else : continue
			
			res[line.id] = line.price_unit * line.quantity * (1-(line.discount or 0.0)/100.0)
			if line.invoice_id.price_type == 'tax_included':			
				# remove product taxes
				taxes = tax_obj.compute_inv(cr, uid,line.product_id.taxes_id,
											res[line.id],
											line.quantity)
				amount = 0
				for t in taxes : amount = amount + t['amount']
				res[line.id]= res[line.id] - amount
			## Add line taxes
			taxes = tax_obj.compute(cr, uid,line.invoice_line_tax_id, res[line.id], line.quantity)
			amount = 0
			for t in taxes : amount = amount + t['amount']
			cur = cur or line.invoice_id.currency_id					
			res[line.id]= cur.round(cr, uid, cur, res[line.id] + amount) 
		return res


	_columns = {
		'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal w/o vat'),
		'price_subtotal_incl': fields.function(_amount_line_incl, method=True, string='Subtotal'),
	}

	#
	# Compute a tax amount for each kind of tax :
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
			price_unit = line.price_unit
			if line.product_id:
				prod_taxe_ids = [ t.id for t in line.product_id.taxes_id ]
				prod_taxe_ids.sort()
				line_taxe_ids = [ t.id for t in line.invoice_line_tax_id]
				line_taxe_ids.sort()
			if line.product_id and prod_taxe_ids != line_taxe_ids :
				price_unit= reduce( lambda x, y: x-y['amount'],
									tax_obj.compute_inv(cr, uid,line.product_id.taxes_id,
														line.price_unit * (1-(line.discount or 0.0)/100.0), line.quantity),
									price_unit)
				taxes =tax_obj.compute(cr, uid, line.invoice_line_tax_id,
									   (price_unit *(1.0-(line['discount'] or 0.0)/100.0)),
									   line.quantity, inv.address_invoice_id.id)
			else:
				taxes= tax_obj.compute_inv(cr, uid, line.invoice_line_tax_id,
										   (line.price_unit *(1.0-(line['discount'] or 0.0)/100.0)),
										   line.quantity, inv.address_invoice_id.id)

			res.append( {
				'type':'src', 
				'name':line.name, 
				'price_unit':price_unit, 
				'quantity':line.quantity, 
				'price':line.quantity*price_unit * (1.0- (line.discount or 0.0)/100.0),
				'account_id':line.account_id.id,
				'product_id': line.product_id.id,
				'uos_id':line.uos_id.id,
				'account_analytic_id':line.account_analytic_id.id,
			})
			for tax in taxes:
				val={}
				val['invoice_id'] = inv.id
				val['name'] = tax['name']
				val['amount'] = cur_obj.round(cr, uid, cur, tax['amount'])
				val['manual'] = False
				val['sequence'] = tax['sequence']
				val['base'] = tax['price_unit'] * line['quantity']

				res[-1]['price']-=tax['amount']

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
			res[-1]['price']=cur_obj.round(cr, uid, cur, res[-1]['price'])
		# delete automatic tax lines for this invoice
		cr.execute("DELETE FROM account_invoice_tax WHERE NOT manual AND invoice_id=%d", (invoice_id,))
		for t in tax_grouped.values():
			ait_obj.create(cr, uid, t)
		return res
account_invoice_line()
