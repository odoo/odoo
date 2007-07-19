
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

from osv import fields
from osv import osv

class account_analytic_line(osv.osv):
	_name = 'account.analytic.line'
	_description = 'Analytic lines'
	_columns = {
		'name' : fields.char('Description', size=256, required=True),
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
		'ref': fields.char('Ref.', size=32),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
	_order = 'date'
	def _check_company(self, cr, uid, ids):
		lines = self.browse(cr, uid, ids)
		for l in lines:
			if l.move_id and not l.account_id.company_id.id == l.move_id.account_id.company_id.id:
				return False
		return True
	_constraints = [
		(_check_company, 'You can not create analytic line that is not in the same company than the account line', ['account_id'])
	]
	
	def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount, unit=False, context={}):
		if unit_amount and prod_id:
			rate = 1
			if unit:
				uom_obj = self.pool.get('product.uom')
				hunit = uom_obj.browse(cr, uid, unit)
				rate = hunit.factor
			product_obj = self.pool.get('product.product')
			prod = product_obj.browse(cr, uid, prod_id)
			a = prod.product_tmpl_id.property_account_expense
			if not a:
				a = prod.categ_id.property_account_expense_categ
			if not a:
				raise osv.except_osv('Error !', 'There is no expense account define for this product: "%s" (id:%d)' % (prod.name, prod.id,))
			return {'value' : {'amount' : -round(unit_amount * prod.standard_price * rate,2), 'general_account_id':a[0]}}
		return {}

account_analytic_line()


class timesheet_invoice(osv.osv):
	_name = "report.hr.timesheet.invoice.journal"
	_description = "Analytic account costs and revenues"
	_auto = False
	_columns = {
		'name': fields.date('Month', readonly=True),
		'account_id':fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, select=True),
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
				substring(l.date for 7)||'-01' as name,
				sum(
					CASE WHEN l.amount>0 THEN 0 ELSE l.amount
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
				substring(l.date for 7),
				journal_id,
				account_id
		)""")
timesheet_invoice()
