##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import time
import operator

from osv import fields
from osv import osv

#
# Model definition
#

class account_analytic_account(osv.osv):
	_name = 'account.analytic.account'

	def _credit_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			node_balance = reduce(operator.add, [-line.amount for line in account.line_ids if line.amount<0], 0)
			child_balance = reduce(operator.add, [child.credit for child in account.child_ids], 0)
			res[account.id] = node_balance + child_balance
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _debit_calc(self, cr, uid, ids, name, arg, context={}):
		# XXX to be improved like in account.account
		res = {}
		for account in self.browse(cr, uid, ids):
			node_balance = reduce(operator.add, [line.amount for line in account.line_ids if line.amount>0], 0)
			child_balance = reduce(operator.add, [child.debit for child in account.child_ids], 0)
			res[account.id] = node_balance + child_balance
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _balance_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			node_balance = reduce(operator.add, [line.amount for line in account.line_ids], 0)
			child_balance = reduce(operator.add,
				[self.pool.get('res.currency').compute(cr, uid, 
					child.company_id.currency_id.id, 
					account.company_id.currency_id.id, child.balance, context=context)
				for child in account.child_ids], 0)
			res[account.id] = node_balance + child_balance
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _quantity_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			node_balance = reduce(operator.add, [line.unit_amount for line in account.line_ids], 0)
			child_balance = reduce(operator.add, [child.quantity for child in account.child_ids], 0)
			res[account.id] = node_balance + child_balance
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def name_get(self, cr, uid, ids, context={}):
		if not len(ids):
			return []
		reads = self.read(cr, uid, ids, ['name','parent_id'], context)
		res = []
		for record in reads:
			name = record['name']
			if record['parent_id']:
				name = record['parent_id'][1]+' / '+name
			res.append((record['id'], name))
		return res

	def _complete_name_calc(self, cr, uid, ids, prop, unknow_none, unknow_dict):
		res = self.name_get(cr, uid, ids)
		return dict(res)

	def _get_company_currency(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for rec in self.browse(cr, uid, ids, context):
			result[rec.id] = (rec.company_id.currency_id.id,rec.company_id.currency_id.code) or False
		return result

	_columns = {
		'name' : fields.char('Account name', size=64, required=True),
		'complete_name': fields.function(_complete_name_calc, method=True, type='char', string='Account Name'),
		'code' : fields.char('Account code', size=24),
		'active' : fields.boolean('Active'),
		'type': fields.selection([('view','View'), ('normal','Normal')], 'type'),
		'description' : fields.text('Description'),
		'parent_id': fields.many2one('account.analytic.account', 'Parent Cost account', select=True),
		'child_ids': fields.one2many('account.analytic.account', 'parent_id', 'Childs Accounts'),
		'line_ids': fields.one2many('account.analytic.line', 'account_id', 'Analytic entries'),
		'balance' : fields.function(_balance_calc, method=True, type='float', string='Balance'),
		'debit' : fields.function(_debit_calc, method=True, type='float', string='Debit'),
		'credit' : fields.function(_credit_calc, method=True, type='float', string='Credit'),
		'quantity': fields.function(_quantity_calc, method=True, type='float', string='Quantity'),
		'quantity_max': fields.float('Maximal quantity'),
		'partner_id' : fields.many2one('res.partner', 'Associated partner'),
		'contact_id' : fields.many2one('res.partner.address', 'Contact'),
		'user_id' : fields.many2one('res.users', 'Account Manager'),
		'date_start': fields.date('Date Start'),
		'date': fields.date('Date End'),
		'stats_ids': fields.one2many('report.hr.timesheet.invoice.journal', 'account_id', string='Statistics', readonly=True),
		'company_id': fields.many2one('res.company', 'Company', required=True),
		'company_currency_id': fields.function(_get_company_currency, method=True, type='many2one', relation='res.currency', string='Currency'),
	}

	def _default_company(self, cr, uid, context={}):
		user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		if user.company_id:
			return user.company_id.id
		return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
	_defaults = {
		'active' : lambda *a : True,
		'type' : lambda *a : 'normal',
		'company_id': _default_company,
	}

	_order = 'parent_id desc,code'

	def create(self, cr, uid, vals, ctx={}):
		parent_id = vals.get('parent_id', 0)
		if ('code' not in vals or not vals['code']) and not parent_id:
			vals['code'] = self.pool.get('ir.sequence').get(cr, uid, 'account.analytic.account')
		return super(account_analytic_account, self).create(cr, uid, vals, ctx)


	def on_change_parent(self, cr, uid, id, parent_id):
		if not parent_id:
			return {}
		parent = self.read(cr, uid, [parent_id], ['partner_id','code'])[0]
		childs = self.search(cr, uid, [('parent_id', '=', parent_id), ('active', '=', 1)]) + self.search(cr, uid, [('parent_id', '=', parent_id), ('active', '=', 0)])
		numchild = len(childs)
		if parent['partner_id']:
			partner = parent['partner_id'][0]
		else:
			partner = False
		res = {'value' : {'code' : '%s - %03d' % (parent['code'] or '', numchild + 1),}}
		if partner:
			res['value']['partner_id'] = partner
		return res

	def name_search(self, cr, uid, name, args=[], operator='ilike', context={}):
		account = self.search(cr, uid, [('code', '=', name)]+args)
		if not account:
			account = self.search(cr, uid, [('name', 'ilike', '%%%s%%' % name)]+args)
			newacc = account
			while newacc:
				newacc = self.search(cr, uid, [('parent_id', 'in', newacc)]+args)
				account+=newacc
		return self.name_get(cr, uid, account, context=context)

account_analytic_account()


class account_analytic_journal(osv.osv):
	_name = 'account.analytic.journal'
	_columns = {
		'name' : fields.char('Journal name', size=64, required=True),
		'code' : fields.char('Journal code', size=8),
		'active' : fields.boolean('Active'),
		'type': fields.selection([('sale','Sale'), ('purchase','Purchase'), ('cash','Cash'), ('general','General'), ('situation','Situation')], 'Type', size=32, required=True, help="Gives the type of the analytic journal. When a document (eg: an invoice) needs to create analytic entries, Tiny ERP will look for a matching journal of the same type."),
		'line_ids' : fields.one2many('account.analytic.line', 'journal_id', 'Lines'),
	}
	_defaults = {
		'active': lambda *a: True,
		'type': lambda *a: 'general',
	}
account_analytic_journal()


# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------

class account_analytic_budget_post(osv.osv):
	_name = 'account.analytic.budget.post'
	_description = 'Budget item'
	_columns = {
		'code': fields.char('Code', size=64, required=True),
		'name': fields.char('Name', size=256, required=True),
		'sens': fields.selection( [('charge','Charge'), ('produit','Product')], 'Direction', required=True),
		'dotation_ids': fields.one2many('account.analytic.budget.post.dotation', 'post_id', 'Expenses'),
		'account_ids': fields.many2many('account.analytic.account', 'account_analytic_budget_rel', 'budget_id', 'account_id', 'Accounts'),
	}
	_defaults = {
		'sens': lambda *a: 'produit',
	}

	def spread(self, cr, uid, ids, fiscalyear_id=False, quantity=0.0, amount=0.0):

		dobj = self.pool.get('account.analytic.budget.post.dotation')
		for o in self.browse(cr, uid, ids):
			# delete dotations for this post
			dobj.unlink(cr, uid, dobj.search(cr, uid, [('post_id','=',o.id)]))

			# create one dotation per period in the fiscal year, and spread the total amount/quantity over those dotations
			fy = self.pool.get('account.fiscalyear').browse(cr, uid, [fiscalyear_id])[0]
			num = len(fy.period_ids)
			for p in fy.period_ids:
				dobj.create(cr, uid, {'post_id': o.id, 'period_id': p.id, 'quantity': quantity/num, 'amount': amount/num})
		return True
account_analytic_budget_post()

class account_analytic_budget_post_dotation(osv.osv):
	_name = 'account.analytic.budget.post.dotation'
	_description = "Budget item endowment"
	_columns = {
		'name': fields.char('Name', size=64),
		'post_id': fields.many2one('account.analytic.budget.post', 'Item', select=True),
		'period_id': fields.many2one('account.period', 'Period'),
		'quantity': fields.float('Quantity', digits=(16,2)),
		'amount': fields.float('Amount', digits=(16,2)),
	}
account_analytic_budget_post_dotation()
