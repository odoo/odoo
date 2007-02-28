##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: hr.py 3751 2006-08-09 13:15:36Z mvd $
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

from mx import DateTime
import time

from osv import fields, osv

def _employee_get(obj,cr,uid,context={}):
	ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
	if ids:
		return ids[0]
	return False

class hr_expense_expense(osv.osv):
	def _amount(self, cr, uid, ids, field_name, arg, context):
		id_set = ",".join(map(str, ids))
		cr.execute("SELECT s.id,COALESCE(SUM(l.unit_amount*l.unit_quantity),0) AS amount FROM hr_expense_expense s LEFT OUTER JOIN hr_expense_line l ON (s.id=l.expense_id) WHERE s.id IN ("+id_set+") GROUP BY s.id ")
		res = dict(cr.fetchall())
		return res

	_name = "hr.expense.expense"
	_description = "Expense"
	_columns = {
		'name': fields.char('Expense Sheet', size=128, required=True),
		'id': fields.integer('Sheet ID', readonly=True),
		'ref': fields.char('Reference', size=32),
		'date': fields.date('Date'),
		'account_id': fields.many2one('account.account', 'Payable Account'),
		'journal_id': fields.many2one('account.journal', 'Journal'),
		'analytic_journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal'),
		'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
		'user_id': fields.many2one('res.users', 'User', required=True),
		'date_confirm': fields.date('Date Confirmed'),
		'date_valid': fields.date('Date Valided'),
		'user_valid': fields.many2one('res.users', 'Validation User'),

		'account_move_id': fields.many2one('account.move', 'Account Move'),
		'line_ids': fields.one2many('hr.expense.line', 'expense_id', 'Expense Lines'),
		'note': fields.text('Note'),

		# fields.function
		'amount': fields.function(_amount, method=True, string='Total Amount'),
		'move_id': fields.many2one('account.move','Accounting Entries'),

		'state': fields.selection([
			('draft', 'Draft'),
			('confirm', 'Waiting confirmation'),
			('accepted', 'Accepted'),
			('paid', 'Reimbursed'),
			('canceled', 'Canceled')],
			'State', readonly=True),
	}
	_defaults = {
		'date' : lambda *a: time.strftime('%Y-%m-%d'),
		'state': lambda *a: 'draft',
		'employee_id' : _employee_get,
		'user_id' : lambda cr,uid,id,c={}: id
	}
	def expense_confirm(self, cr, uid, ids, *args):
		#for exp in self.browse(cr, uid, ids):
		self.write(cr, uid, ids, {
			'state':'confirm',
			'date_confirm': time.strftime('%Y-%m-%d')
		})
		return True

	def expense_accept(self, cr, uid, ids, *args):
		for exp in self.browse(cr, uid, ids):
			if not (exp.journal_id and exp.account_id):
				raise osv.except_osv('No account or journal defined !', 'You have to define a journal and an account to validate this expense note.')
			lines = []
			total = 0
			for line in exp.line_ids:
				if line.product_id:
					acc = line.product_id.product_tmpl_id.property_account_expense
					if not acc:
						acc = line.product_id.categ_id.property_account_expense_categ
					acc = acc[0]
					lines.append({
						'name': line.name,
						'date': line.date_value or time.strftime('%Y-%m-%d'),
						'quantity': line.unit_quantity,
						'ref': line.ref,
						'debit': (line.total_amount>0 and line.total_amount) or 0,
						'credit': (line.total_amount<0 and -line.total_amount) or 0,
						'account_id': acc,
					})
					total += line.total_amount
					if line.analytic_account:
						if not exp.analytic_journal_id:
							raise osv.except_osv('No analytic journal defined !', 'You have to define an analytic journal to validate this expense note.')


						self.pool.get('account.analytic.line').create(cr, uid, {
							'name': line.name,
							'date': line.date_value,
							'product_id': line.product_id.id,
							'product_uom_id': line.uom_id.id,
							'unit_amount': line.unit_quantity,
							'code': line.ref,
							'amount': -line.total_amount,
							'journal_id': exp.analytic_journal_id.id,
							'general_account_id': acc,
							'account_id': line.analytic_account.id
						})
			move_id = False
			if lines:
				lines.append({
					'name': exp.name+'['+str(exp.id)+']',
					'date': exp.date or time.strftime('%Y-%m-%d'),
					'ref': exp.ref,
					'debit': (total<0 and -total) or 0,
					'credit': (total>0 and total) or 0,
					'account_id': exp.account_id.id,
				})
				if exp.journal_id.sequence_id:
					name = self.pool.get('ir.sequence').get_id(cr, uid, exp.journal_id.sequence_id.id)
				else:
					name = "EXP "+time.strftime('%Y-%m-%d')
				move_id = self.pool.get('account.move').create(cr, uid, {
					'name': name,
					'journal_id': exp.journal_id.id,
					'line_id': map(lambda x: (0,0,x), lines)
				})
			self.write(cr, uid, [exp.id], {
				'move_id': move_id,
				'state':'accepted',
				'date_valid': time.strftime('%Y-%m-%d'),
				'user_valid': uid
			})
		return True

	def expense_canceled(self, cr, uid, ids, *args):
		self.write(cr, uid, ids, {'state':'canceled'})
		return True

	def expense_paid(self, cr, uid, ids, *args):
		self.write(cr, uid, ids, {'state':'paid'})
		return True
hr_expense_expense()


class hr_expense_line(osv.osv):
	_name = "hr.expense.line"
	_description = "Expense Line"
	def _amount(self, cr, uid, ids, field_name, arg, context):
		if not len(ids):
			return {}
		id_set = ",".join(map(str, ids))
		cr.execute("SELECT l.id,COALESCE(SUM(l.unit_amount*l.unit_quantity),0) AS amount FROM hr_expense_line l WHERE id IN ("+id_set+") GROUP BY l.id ")
		res = dict(cr.fetchall())
		return res

	_columns = {
		'name': fields.char('Short Description', size=128, required=True),
		'date_value': fields.date('Date', required=True),
		'expense_id': fields.many2one('hr.expense.expense', 'Expense', ondelete='cascade', select=True),
		'total_amount': fields.function(_amount, method=True, string='Total'),
		'unit_amount': fields.float('Unit Price', readonly=True, states={'draft':[('readonly',False)]}),
		'unit_quantity': fields.float('Quantities', readonly=True, states={'draft':[('readonly',False)]}),
		'product_id': fields.many2one('product.product', 'Product', readonly=True, states={'draft':[('readonly',False)]}),
		'uom_id': fields.many2one('product.uom', 'UoM', readonly=True, states={'draft':[('readonly',False)]}),
		'description': fields.text('Description'),
		'analytic_account': fields.many2one('account.analytic.account','Analytic account'),
		'ref': fields.char('Reference', size=32),
		'sequence' : fields.integer('Sequence'),
	}
	_defaults = {
		'unit_quantity': lambda *a: 1,
		'date_value' : lambda *a: time.strftime('%Y-%m-%d'),
	}
	_order = "sequence"
	def onchange_product_id(self, cr, uid, ids, product_id, uom_id, context={}):
		v={}
		if product_id:
			product=self.pool.get('product.product').browse(cr,uid,product_id, context=context)
			v['name']=product.name
			v['unit_amount']=product.standard_price
			if not uom_id:
				v['uom_id']=product.uom_id.id
		return {'value':v}

hr_expense_line()

# vim:tw=0:noexpandtab
