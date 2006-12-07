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

import netsvc
from osv import fields, osv

class account_tax(osv.osv):
	_inherit = 'account.tax'
	_description = 'Tax'
	_columns = {
		'python_compute_inv':fields.text('Python Code (VAT Incl)'),
	}
	_defaults = {
		'python_compute_inv': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n\nresult = price_unit * 0.10''',
	}
	def _unit_compute_inv(self, cr, uid, ids, price_unit, address_id=None):
		taxes = self.browse(cr, uid, ids)
		return self._unit_compute_inv_br(cr, uid, taxes, price_unit, address_id)

	def _unit_compute_inv_br(self, cr, uid, taxes, price_unit, address_id=None):
		taxes = self._applicable(cr, uid, taxes, price_unit, address_id)

		res = []
		for tax in taxes:
			# we compute the amount for the current tax object and append it to the result
			if tax.type=='percent':
				amount = price_unit - (price_unit / (1 + tax.amount))
				res.append({'id':tax.id, 'name':tax.name, 'amount':amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id})
			elif tax.type=='fixed':
				res.append({'id':tax.id, 'name':tax.name, 'amount':tax.amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id})
			elif tax.type=='code':
				address = address_id and self.pool.get('res.partner.address').browse(cr, uid, address_id) or None
				localdict = {'price_unit':price_unit, 'address':address}
				exec tax.python_compute_inv in localdict
				amount = localdict['result']
				res.append({
					'id': tax.id,
					'name': tax.name,
					'amount': amount,
					'account_collected_id': tax.account_collected_id.id,
					'account_paid_id': tax.account_paid_id.id
				})
			amount2 = res[-1]['amount']
			if len(tax.child_ids):
				if tax.child_depend:
					del res[-1]
					amount = amount2
				else:
					amount = amount2
			for t in tax.child_ids:
				parent_tax = self._unit_compute_inv_br(cr, uid, [t], amount, address_id)
				res.extend(parent_tax)
		return res

	def compute_inv(self, cr, uid, ids, price_unit, quantity, address_id=None):
		"""
		Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.
		Price Unit is a VAT included price

		RETURN:
			[ tax ]
			tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
			one tax for each tax id in IDS and their childs
		"""
		res = self._unit_compute_inv(cr, uid, ids, price_unit, address_id)
		for r in res:
			r['amount'] *= quantity
		return res
account_tax()

