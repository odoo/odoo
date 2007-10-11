# -*- coding: utf-8 -*- 
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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
import operator
from osv import osv, fields

class account_analytic_account(osv.osv):
	_name = "account.analytic.account"
	_inherit = "account.analytic.account"

	def _ca_invoiced_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			cr.execute("select account_analytic_line.account_id, sum(amount) \
					from account_analytic_line \
					join account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id  \
					where account_analytic_line.account_id IN (%s) \
						and account_analytic_journal.type = 'sale' \
					group by account_analytic_line.account_id" % acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = round(sum,2)
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _ca_to_invoice_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		res2 = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			# Amount uninvoiced hours to invoice at sale price
			acc_set = ",".join(map(str, ids2))
			cr.execute("""SELECT account_analytic_account.id, \
						sum (product_template.list_price * \
							account_analytic_line.unit_amount * \
							((100-hr_timesheet_invoice_factor.factor)/100)) \
							AS ca_to_invoice \
					FROM product_template \
					join product_product \
						on product_template.id = product_product.product_tmpl_id \
					JOIN account_analytic_line \
						on account_analytic_line.product_id = product_product.id \
					JOIN account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id \
					JOIN account_analytic_account \
						on account_analytic_account.id = account_analytic_line.account_id \
					JOIN hr_timesheet_invoice_factor \
						on hr_timesheet_invoice_factor.id = account_analytic_account.to_invoice \
					WHERE account_analytic_account.id IN (%s) \
						AND account_analytic_journal.type='general' \
						AND account_analytic_line.invoice_id is null \
					GROUP BY account_analytic_account.id;"""%acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = round(sum,2)

			# Expense amount and purchase invoice
			acc_set = ",".join(map(str, ids2))
			cr.execute ("select account_analytic_line.account_id, sum(amount) \
					from account_analytic_line \
					join account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id \
					where account_analytic_line.account_id IN (%s) \
						and account_analytic_journal.type = 'purchase' \
					GROUP BY account_analytic_line.account_id;"%acc_set)
			for account_id, sum in cr.fetchall():
				res2[account_id] = round(sum,2)
		# sum both result on account_id
		for id in ids:
			res[id] = round(res.get(id, 0.0),2) + round(res2.get(id, 0.0),2)
		return res

	def _hours_qtt_non_invoiced_calc (self, cr, uid, ids, name, arg, context={}):
		res = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			cr.execute("select account_analytic_line.account_id, sum(unit_amount) \
					from account_analytic_line \
					join account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id \
					where account_analytic_line.account_id IN (%s) \
						and account_analytic_journal.type='general' \
						and invoice_id is null \
					GROUP BY account_analytic_line.account_id;"%acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = round(sum,2)
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res			

	def _hours_quantity_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			cr.execute("select account_analytic_line.account_id,sum(unit_amount) \
					from account_analytic_line \
					join account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id \
					where account_analytic_line.account_id IN (%s) \
						and account_analytic_journal.type='general' \
					GROUP BY account_analytic_line.account_id"%acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = round(sum,2)
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _total_cost_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			cr.execute("""select account_analytic_line.account_id,sum(amount) \
					from account_analytic_line \
					join account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id \
					where account_analytic_line.account_id IN (%s) \
						and amount<0 \
					GROUP BY account_analytic_line.account_id"""%acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = round(sum,2)
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _ca_theorical_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		res2 = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			# First part with expense and purchase
			cr.execute("""select account_analytic_line.account_id,sum(amount) \
					from account_analytic_line \
					join account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id \
					where account_analytic_line.account_id IN (%s) \
						and account_analytic_journal.type = 'purchase' \
					GROUP BY account_analytic_line.account_id"""%acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = round(sum,2)

			# Second part with timesheet (with invoice factor)
			acc_set = ",".join(map(str, ids2))
			cr.execute("""select account_analytic_line.account_id as account_id, \
						sum((account_analytic_line.unit_amount * pt.list_price) \
							- (account_analytic_line.unit_amount * pt.list_price \
								* hr.factor)) as somme
					from account_analytic_line \
					join account_analytic_journal \
						on account_analytic_line.journal_id = account_analytic_journal.id \
					join product_product pp \
						on (account_analytic_line.product_id = pp.id) \
					join product_template pt \
						on (pp.product_tmpl_id = pt.id) \
					join account_analytic_account a \
						on (a.id=account_analytic_line.account_id) \
					join hr_timesheet_invoice_factor hr \
						on (hr.id=a.to_invoice) \
				where account_analytic_line.account_id IN (%s) \
					and account_analytic_journal.type = 'general' \
					and a.to_invoice IS NOT NULL \
				GROUP BY account_analytic_line.account_id"""%acc_set)
			for account_id, sum in cr.fetchall():
				res2[account_id] = round(sum,2)

		# sum both result on account_id
		for id in ids:
			res[id] = round(res.get(id, 0.0),2) + round(res2.get(id, 0.0),2)
		return res

	def _last_worked_date_calc (self, cr, uid, ids, name, arg, context={}):
		res = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			cr.execute("select account_analytic_line.account_id, max(date) \
					from account_analytic_line \
					where account_id IN (%s) \
						and invoice_id is null \
					GROUP BY account_analytic_line.account_id" % acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = sum
		for id in ids:
			res[id] = res.get(id, '')
		return res

	def _last_invoice_date_calc (self, cr, uid, ids, name, arg, context={}):
		res = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			cr.execute ("select account_analytic_line.account_id, \
						date(max(account_invoice.date_invoice)) \
					from account_analytic_line \
					join account_invoice \
						on account_analytic_line.invoice_id = account_invoice.id \
					where account_analytic_line.account_id IN (%s) \
						and account_analytic_line.invoice_id is not null \
					GROUP BY account_analytic_line.account_id"%acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = sum
		for id in ids:
			res[id] = res.get(id, '')
		return res

	def _last_worked_invoiced_date_calc (self, cr, uid, ids, name, arg, context={}):
		res = {}
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		if ids2:
			acc_set = ",".join(map(str, ids2))
			cr.execute("select account_analytic_line.account_id, max(date) \
					from account_analytic_line \
					where account_id IN (%s) \
						and invoice_id is not null \
					GROUP BY account_analytic_line.account_id;"%acc_set)
			for account_id, sum in cr.fetchall():
				res[account_id] = sum
		for id in ids:
			res[id] = res.get(id, '')
		return res

	def _remaining_hours_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			if account.quantity_max <> 0:
				res[account.id] = account.quantity_max - account.hours_quantity
			else:
				res[account.id]=0.0
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _hours_qtt_invoiced_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			res[account.id] = account.hours_quantity - account.hours_qtt_non_invoiced
			if res[account.id] < 0:
				res[account.id]=0.0
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _revenue_per_hour_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			if account.hours_qtt_invoiced == 0:
				res[account.id]=0.0
			else:
				res[account.id] = account.ca_invoiced / account.hours_qtt_invoiced
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _real_margin_rate_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			if account.ca_invoiced == 0:
				res[account.id]=0.0
			elif account.real_margin <> 0.0:
				res[account.id] = (account.ca_invoiced / account.real_margin) * 100
			else:
				res[account.id] = 0.0
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _remaining_ca_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			if account.amount_max <> 0:
				res[account.id] = account.amount_max - account.ca_invoiced
			else:
				res[account.id]=0.0
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _real_margin_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			res[account.id] = account.ca_invoiced + account.total_cost
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	def _theorical_margin_calc(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for account in self.browse(cr, uid, ids):
			res[account.id] = account.ca_theorical + account.total_cost
		for id in ids:
			res[id] = round(res.get(id, 0.0),2)
		return res

	_columns ={
		'ca_invoiced': fields.function(_ca_invoiced_calc, method=True, type='float', string='Invoiced amount'),
		'total_cost': fields.function(_total_cost_calc, method=True, type='float', string='Total cost'),
		'ca_to_invoice': fields.function(_ca_to_invoice_calc, method=True, type='float', string='Uninvoiced amount'),
		'ca_theorical': fields.function(_ca_theorical_calc, method=True, type='float', string='Theorical revenue'),
		'hours_quantity': fields.function(_hours_quantity_calc, method=True, type='float', string='Hours tot'),
		'last_invoice_date': fields.function(_last_invoice_date_calc, method=True, type='date', string='Last invoice date'),
		'last_worked_invoiced_date': fields.function(_last_worked_invoiced_date_calc, method=True, type='date', string='Last invoiced worked date'),
		'last_worked_date': fields.function(_last_worked_date_calc, method=True, type='date', string='Last worked date'),
		'hours_qtt_non_invoiced': fields.function(_hours_qtt_non_invoiced_calc, method=True, type='float', string='Uninvoiced hours'),
		'hours_qtt_invoiced': fields.function(_hours_qtt_invoiced_calc, method=True, type='float', string='Invoiced hours'),
		'remaining_hours': fields.function(_remaining_hours_calc, method=True, type='float', string='Remaining hours'),
		'remaining_ca': fields.function(_remaining_ca_calc, method=True, type='float', string='Remaining revenue'),
		'revenue_per_hour': fields.function(_revenue_per_hour_calc, method=True, type='float', string='Revenue per hours (real)'),
		'real_margin': fields.function(_real_margin_calc, method=True, type='float', string='Real margin'),
		'theorical_margin': fields.function(_theorical_margin_calc, method=True, type='float', string='Theorical margin'),
		'real_margin_rate': fields.function(_real_margin_rate_calc, method=True, type='float', string='Real margin rate (%)'),
		'month_ids': fields.one2many('account_analytic_analysis.summary.month', 'account_id', 'Month', readonly=True),
		'user_ids': fields.one2many('account_analytic_analysis.summary.user', 'account_id', 'User', readonly=True),
	}
account_analytic_account()

class account_analytic_account_summary_user(osv.osv):
	_name = "account_analytic_analysis.summary.user"
	_description = "Hours summary by user"
	_order='name'
	_auto = False
	_columns = {
		'account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
		'unit_amount': fields.float('Total Time', digits=(16,2), readonly=True),
		'name' : fields.many2one('res.users','User'),
	}
	def init(self, cr):
		cr.execute("""
			create or replace view account_analytic_analysis_summary_user as (
				select
					id,
					unit_amount,
					account_id,
					name from (
						select
							min(account_analytic_line.id) as id, 
							user_id as name,
							account_id, 
							sum(unit_amount) as unit_amount 
						from 
							account_analytic_line 
						join 
							account_analytic_journal on account_analytic_line.journal_id = account_analytic_journal.id 
						where 
							account_analytic_journal.type = 'general'
						group by
							account_id, user_id 
						order by
							user_id,account_id asc )as 
					sous_account_analytic_analysis_summary_user
					order by
						name desc,account_id)""")
account_analytic_account_summary_user()

class account_analytic_account_summary_month(osv.osv):
	_name = "account_analytic_analysis.summary.month"
	_description = "Hours summary by month"
	_auto = False
	_columns = {
		'account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
		'unit_amount': fields.float('Total Time', digits=(16,2), readonly=True),
		'name': fields.char('Month', size=25, readonly=True),
	}
	def init(self, cr):
		cr.execute("""create or replace view account_analytic_analysis_summary_month as ( 
			select id, unit_amount,account_id, sort_month,month as name from ( 
			select 
				min(account_analytic_line.id) as id, 
				date_trunc('month', date) as sort_month, 
				account_id, 
				to_char(date,'Mon YYYY') as month, 
				sum(unit_amount) as unit_amount 
			from 
				account_analytic_line join account_analytic_journal on account_analytic_line.journal_id = account_analytic_journal.id 
			where 
				account_analytic_journal.type = 'general' 
			group by 
				sort_month, month, account_id 
			order by 
				sort_month,account_id asc 
		)as sous_account_analytic_analysis_summary_month order by sort_month,account_id)""")
			
account_analytic_account_summary_month()

