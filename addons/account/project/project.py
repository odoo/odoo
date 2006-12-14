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
			child_balance = reduce(operator.add, [child.balance for child in account.child_ids], 0)
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


	_columns = {
		'name' : fields.char('Account name', size=64, required=True),
		'complete_name': fields.function(_complete_name_calc, method=True, type='char', string='Account Name'),
		'code' : fields.char('Account code', size=8),
		'active' : fields.boolean('Active'),
		'type': fields.selection([('view','View'), ('normal','Normal')], 'type'),
		'description' : fields.text('Description'),
		'parent_id': fields.many2one('account.analytic.account', 'Parent Cost account', select=True),
		'child_ids': fields.one2many('account.analytic.account', 'parent_id', 'Childs Accounts'),
		'line_ids': fields.one2many('account.analytic.line', 'account_id', 'Analytic entries'),
		'balance' : fields.function(_balance_calc, method=True, type='float', string='Balance'),
		'debit' : fields.function(_debit_calc, method=True, type='float', string='Balance'),
		'credit' : fields.function(_credit_calc, method=True, type='float', string='Balance'),
		'quantity': fields.function(_quantity_calc, method=True, type='float', string='Quantity'),
		'quantity_max': fields.float('Maximal quantity'),
		'partner_id' : fields.many2one('res.partner', 'Associated partner'),
		'contact_id' : fields.many2one('res.partner.address', 'Contact'),
		'user_id' : fields.many2one('res.users', 'Account Manager'),
		'date_start': fields.date('Date Start'),
		'date': fields.date('Date End'),
		'stats_ids': fields.one2many('report.hr.timesheet.invoice.journal', 'account_id', string='Statistics', readonly=True),
	}

	_defaults = {
		'active' : lambda *a : True,
		'type' : lambda *a : 'normal',
	}

	_order = 'parent_id desc,code'

	def create(self, cr, uid, vals, ctx={}):
		parent_id = vals.get('parent_id', 0)
		if ('code' not in vals or not vals['code']) and not parent_id:
			vals['code'] = self.pool.get('ir.sequence').get(cr, uid, 'account.analytic.account')
		elif parent_id:
			parent = self.read(cr, uid, [parent_id], ['parent_id'])[0]
			childs = self.search(cr, uid, [('parent_id', '=', parent_id), ('active', '=', 1)]) + self.search(cr, uid, [('parent_id', '=', parent_id), ('active', '=', 0)])
			vals['code'] = '%03d' % (len(childs) + 1,)
		return super(account_analytic_account, self).create(cr, uid, vals, ctx)


	def on_change_parent(self, cr, uid, id, parent_id):
		if not parent_id:
			return {'value': {'code': False, 'partner_id': ''}}
		parent = self.read(cr, uid, [parent_id], ['partner_id'])[0]
		childs = self.search(cr, uid, [('parent_id', '=', parent_id), ('active', '=', 1)]) + self.search(cr, uid, [('parent_id', '=', parent_id), ('active', '=', 0)])
		numchild = len(childs)
		if parent['partner_id']:
			partner = parent['partner_id'][0]
		else:
			partner = False
		return {'value' : {'code' : '%03d' % (numchild + 1,), 'partner_id' : partner}}

	def name_search(self, cr, uid, name, args=[], operator='ilike', context={}):
		codes = name.split('.')
		codes.reverse()
		parent_code = False
		while codes:
			current_code = codes.pop()
			account = self.search(cr, uid, [('parent_id', '=', parent_code), ('code', '=', current_code)]+args)
			if account:
				parent_code = account[0]
			else:
				account = self.search(cr, uid, [('name', 'ilike', '%%%s%%' % name)]+args)
				break
		return self.name_get(cr, uid, account)

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
	
class account_analytic_line(osv.osv):
	_name = 'account.analytic.line'
	_columns = {
		'name' : fields.char('Description', size=128, required=True),
		'date' : fields.date('Date', required=True),
		'amount' : fields.float('Amount', required=True),
		'unit_amount' : fields.float('Quantity'),
		'product_uom_id' : fields.many2one('product.uom', 'UoM'),
		'product_id' : fields.many2one('product.product', 'Product'),
		'account_id' : fields.many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='cascade', select=True),
		'general_account_id' : fields.many2one('account.account', 'General account', required=True, ondelete='cascade'),
		'move_id' : fields.many2one('account.move.line', 'General entry', ondelete='cascade', select=True),
		'journal_id' : fields.many2one('account.analytic.journal', 'Analytic journal', required=True, ondelete='cascade', select=True),
		'code' : fields.char('Code', size=8),
		'user_id' : fields.many2one('res.users', 'User',),
	}
		
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
	_order = 'date'
	
	def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount, unit=False, context={}):
		if unit_amount and prod_id:
			rate = 1
			if unit:
				uom_id = self.pool.get('product.uom')
				hunit = uom_id.browse(cr, uid, unit)
				rate = hunit.factor
			uom_id = self.pool.get('product.product')
			prod = uom_id.browse(cr, uid, prod_id)
			a = prod.product_tmpl_id.property_account_expense
			if not a:
				a = prod.categ_id.property_account_expense_categ
			return {'value' : {'amount' : -round(unit_amount * prod.standard_price * rate,2), 'general_account_id':a[0]}}
		return {}

account_analytic_line()

class timesheet_invoice(osv.osv):
	_name = "report.hr.timesheet.invoice.journal"
	_description = "Analytic account costs and revenues"
	_auto = False
	_columns = {
		'name': fields.date('Month', readonly=True),
		'account_id':fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, relate=True, select=True),
		'journal_id': fields.many2one('account.analytic.journal', 'Journal', readonly=True),
		'quantity': fields.float('Quantities', readonly=True),
		'cost': fields.float('Credit', readonly=True),
		'revenue': fields.float('Debit', readonly=True)
	}
	_order = 'name desc, account_id'
	def init(self, cr):
		#cr.execute("""
		#create or replace view report_hr_timesheet_invoice_journal as (
		#	select
		#		min(l.id) as id,
		#		substring(l.create_date for 7)||'-01' as name,
		#		sum(greatest(-l.amount,0)) as cost,
		#		sum(greatest(l.amount,0)) as revenue,
		#		sum(l.unit_amount*u.factor) as quantity,
		#		journal_id,
		#		account_id
		#	from account_analytic_line l
		#		left join product_uom u on (u.id=l.product_uom_id)
		#	group by
		#		substring(l.create_date for 7),
		#		journal_id,
		#		account_id
		#)""")
		cr.execute("""
		create or replace view report_hr_timesheet_invoice_journal as (
			select
				min(l.id) as id,
				substring(l.create_date for 7)||'-01' as name,
				sum(
					CASE WHEN -l.amount>0 THEN 0 ELSE -l.amount
					END
				) as cost,
				sum(
					CASE WHEN l.amount>0 THEN l.amount ELSE 0
					END
				) as revenue,
				sum(l.unit_amount*u.factor) as quantity,
				journal_id,
				account_id
			from account_analytic_line l
				left join product_uom u on (u.id=l.product_uom_id)
			group by
				substring(l.create_date for 7),
				journal_id,
				account_id
		)""")
timesheet_invoice()

