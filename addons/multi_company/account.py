##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: product_extended.py 5702 2007-02-20 15:33:28Z ced $
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

from osv import fields,osv

class account_analytic_account(osv.osv):
	_inherit = 'account.analytic.account'
	_columns = {
		'company_id': fields.many2one('res.company', 'Company'),
	}
	_defaults = {
		'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
	}
account_analytic_account()

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------
class account_account(osv.osv):
	_inherit = "account.account"
	def _get_company_currency(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for rec in self.browse(cr, uid, ids, context):
			result[rec.id] = rec.company_id and (rec.company_id.currency_id.id,rec.company_id.currency_id.code) or False
		return result
	def _balance(self, cr, uid, ids, field_name, arg, context={}):
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		acc_set = ",".join(map(str, ids2))
		res = {}
		cr.execute("SELECT a.id, COALESCE(SUM((l.debit-l.credit)),0) FROM account_account a LEFT JOIN account_move_line l ON (a.id=l.account_id) WHERE a.id IN (%s) and l.active AND l.state<>'draft' GROUP BY a.id" % acc_set)
		for account_id, sum in cr.fetchall():
			res[account_id] = round(sum,2)

		cr.execute("SELECT a.id, a.company_id FROM account_account a where id in (%s)" % acc_set)
		resc = dict(cr.fetchall())

		compc = {}
		for id in ids:
			ids3 = self.search(cr, uid, [('parent_id', 'child_of', [id])])
			to_currency_id = self._company_currency(cr,uid,resc[id],compc,context)
			for idx in ids3:
				if idx <> id:
					res.setdefault(id, 0.0)
					if resc[idx]<>resc[id] and resc[idx] and resc[id]:
						from_currency_id = self._company_currency(cr,uid,resc[idx],compc,context)
						res[id] += self.pool.get('res.currency').compute(cr, uid, from_currency_id, to_currency_id, res.get(idx, 0.0), context=context)
					else:
						res[id] += res.get(idx, 0.0)
		for id in ids:
			res[id] = round(res.get(id,0.0), 2)
		return res

	_columns = {
		'company_currency_id': fields.function(_get_company_currency, method=True, type='many2one', relation='res.currency', string='Currency'),
		'company_id': fields.many2one('res.company', 'Company'),
		'balance': fields.function(_balance, digits=(16,2), method=True, string='Balance'),
	}
	_defaults = {
		'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
	}
account_account()

class account_fiscalyear(osv.osv):
	_inherit = "account.fiscalyear"
	_columns = {
		'company_id': fields.many2one('res.company', 'Company'),
	}
	_defaults = {
		'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
	}
account_fiscalyear()

class account_tax(osv.osv):
	_inherit = 'account.tax'
	_columns = {
		'company_id': fields.many2one('res.company', 'Company'),
	}
	_defaults = {
		'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
	}
account_tax()
