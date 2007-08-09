##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields, osv
import ir

class partner_wh_rebate(osv.osv):
	_name = "res.partner"
	_inherit = "res.partner"
	_columns = {
		'rebate': fields.float('Rebate (%)', digits=(5, 2)),
	}
partner_wh_rebate()

class sale_order_rebate(osv.osv):
	_name = "sale.order"
	_inherit = "sale.order"

	def _amount_wo_rebate(self, cr, uid, ids, field_name, arg, context):
		return super(sale_order_rebate, self)._amount_untaxed(cr, uid, ids, field_name, arg, context)

	def _amount_rebate(self, cr, uid, ids, field_name, arg, context):
		wo_rebate = self._amount_wo_rebate(cr, uid, ids, field_name, arg, context) 
		orders = self.read(cr, uid, ids, ['rebate_percent'], context)
		rebates = dict([(o['id'], o['rebate_percent']) for o in orders])
		res = {}
		for id in ids:
			res[id] = wo_rebate.get(id, 0.0) * (rebates.get(id, 0.0) / 100.0)
		return res

	def _amount_untaxed(self, cr, uid, ids, field_name, arg, context):
		wo_rebate = self._amount_wo_rebate(cr, uid, ids, field_name, arg, context) 
		rebate = self._amount_rebate(cr, uid, ids, field_name, arg, context)
		res = {}
		for id in ids:
			res[id] = wo_rebate.get(id, 0.0) - rebate.get(id, 0.0)
		return res
		
	def _amount_tax(self, cr, uid, ids, field_name, arg, context):
		res = {}
		cur_obj=self.pool.get('res.currency')
		for order in self.browse(cr, uid, ids):
			val = 0.0
			cur=order.pricelist_id.currency_id
			for line in order.order_line:
				for c in self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit, line.product_uom_qty, order.partner_invoice_id.id):
					val += cur_obj.round(cr, uid, cur, (c['amount'] * (100.0 - order.rebate_percent) / 100.0))
			res[order.id] = cur_obj.round(cr, uid, cur, val)
		return res

	_columns = {
		'rebate_percent': fields.float('Rebate (%)', digits=(5, 2), readonly=True, states={'draft':[('readonly',False)]}),
#		'rebate_account': fields.many2one('account.account', 'Rebate account', required=True, readonly=True, states={'draft':[('readonly',False)]}),
		'amount_wo_rebate': fields.function(_amount_wo_rebate, method=True, string='Intermediate sum'),
		'amount_rebate': fields.function(_amount_rebate, method=True, string='Rebate'),
		'amount_untaxed': fields.function(_amount_untaxed, method=True, string='Untaxed Amount'),
		'amount_tax': fields.function(_amount_tax, method=True, string='Taxes'),
	}
	_defaults = {
		'rebate_percent': lambda *a: 0.0,
	}

	#
	# Why not using super().onchange_partner_id ?
	#
	def onchange_partner_id(self, cr, uid, ids, partner_id):
		if not partner_id:
			return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False, 'partner_order_id': False}}
		partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
		addr = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['delivery', 'invoice', 'contact'])
		pricelist = partner.property_product_pricelist.id
		return {
			'value': {
				'rebate_percent': partner.rebate or 0.0, 
				'partner_invoice_id': addr['invoice'],
				'partner_order_id': addr['contact'],
				'partner_shipping_id': addr['delivery'],
				'pricelist_id': pricelist
			}
		}

	def action_invoice_create(self, cr, uid, ids, grouped=False, states=['confirmed','done']):
		assert len(ids)==1, "Can only invoice one sale order at a time"
		invoice_id = super(sale_order_rebate, self).action_invoice_create(cr, uid, ids, grouped, states)
		if invoice_id:
			order = self.browse(cr, uid, ids[0])
			inv_obj = self.pool.get('account.invoice')
			inv_obj.write(cr, uid, [invoice_id], {'rebate_percent': order.rebate_percent})
			inv_obj.button_compute(cr, uid, [invoice_id])
		return invoice_id
sale_order_rebate()

class account_invoice_wh_rebate(osv.osv):
	_name = "account.invoice"
	_inherit = "account.invoice"

	def _amount_wo_rebate(self, cr, uid, ids, field_name, arg, context):
		return super(account_invoice_wh_rebate, self)._amount_untaxed(cr, uid, ids, field_name, arg, context)

	def _amount_untaxed(self, cr, uid, ids, field_name, arg, context):
		un_taxed = super(account_invoice_wh_rebate, self)._amount_untaxed(cr, uid, ids, field_name, arg, context)
		res = {}
		for invoice in self.browse(cr, uid, ids):
			res[invoice.id] = un_taxed[invoice.id] - invoice.rebate_amount
		return res

	_columns = {
		'amount_wo_rebate': fields.function(_amount_wo_rebate, method=True, string='Intermediate sum'),
		'amount_untaxed': fields.function(_amount_untaxed, method=True, string='Untaxed Amount'),
		'rebate_percent': fields.float('Rebate (%)', digits=(5, 2), readonly=True),
		'rebate_amount': fields.float('Rebate amount', digits=(14, 2), readonly=True)
	}
account_invoice_wh_rebate()

class account_invoice_line_wh_rebate(osv.osv):
	_name = "account.invoice.line"
	_inherit = "account.invoice.line"

	def move_line_get(self, cr, uid, invoice_id):
		invoice = self.pool.get('account.invoice').browse(cr, uid, invoice_id)
		res = []
		tax_grouped = {}
		tax_obj = self.pool.get('account.tax')
#TODO: rewrite using browse instead of the manual SQL queries
		cr.execute('SELECT * FROM account_invoice_line WHERE invoice_id=%d', (invoice_id,))
		lines = cr.dictfetchall()
		rebate_percent = invoice.rebate_percent
		rebate_amount = 0.0
		for line in lines:
			price_unit = line['price_unit'] * (100.0 - rebate_percent) / 100.0
			res.append({'type':'src', 'name':line['name'], 'price_unit':price_unit, 'quantity':line['quantity'], 'price':round(line['quantity']*price_unit, 2), 'account_id':line['account_id']})
			cr.execute('SELECT tax_id FROM account_invoice_line_tax WHERE invoice_line_id=%d', (line['id'],))
			rebate_amount += (line['price_unit'] * rebate_percent / 100.0) * line['quantity']
			for (tax_id,) in cr.fetchall():
				# even though we pass only one tax id at a time to compute, it can return several results
				# in case a tax has a parent tax
				sequence = tax_obj.read(cr, uid, [tax_id], ['sequence'])[0]['sequence']
				for tax in tax_obj.compute(cr, uid, [tax_id], price_unit, line['quantity'], invoice.address_invoice_id.id):
					tax['sequence'] = sequence
					if invoice.type in ('out_invoice','in_refund'):
						tax['account_id'] = tax['account_collected_id']
					else:
						tax['account_id'] = tax['account_paid_id']
					key = tax['account_id']
					if not key in tax_grouped:
						tax_grouped[key] = tax
					else:
						tax_grouped[key]['amount'] += tax['amount']
		# delete automatic tax lines for this invoice
		cr.execute("DELETE FROM account_invoice_tax WHERE NOT manual AND invoice_id=%d", (invoice_id,))
		
		# (re)create them
		ait = self.pool.get('account.invoice.tax')
		for t in tax_grouped.values():
			ait.create(cr, uid, {'invoice_id':invoice_id, 'name':t['name'], 'account_id':t['account_id'], 'amount':t['amount'], 'manual':False, 'sequence':t['sequence']})

		# update rebate amount for this invoice
		self.pool.get('account.invoice').write(cr, uid, [invoice_id], {'rebate_amount': rebate_amount})
		return res
account_invoice_line_wh_rebate()

