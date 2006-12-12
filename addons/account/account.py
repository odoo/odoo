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

from tools.misc import currency

import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

class account_payment_term(osv.osv):
	_name = "account.payment.term"
	_description = "Payment Term"
	_columns = {
		'name': fields.char('Payment Term', size=32),
		'active': fields.boolean('Active'),
		'note': fields.text('Description'),
		'line_ids': fields.one2many('account.payment.term.line', 'payment_id', 'Terms')
	}
	_defaults = {
		'active': lambda *a: 1,
	}
	_order = "name"
	def compute(self, cr, uid, id, value, date_ref=False, context={}):
		if not date_ref:
			date_ref = now().strftime('%Y-%m-%d')
		pt = self.browse(cr, uid, id, context)
		amount = value
		result = []
		for line in pt.line_ids:
			if line.value=='fixed':
				amt = line.value_amount
			elif line.value=='procent':
				amt = round(amount * line.value_amount,2)
			elif line.value=='balance':
				amt = amount
			if amt:
				next_date = mx.DateTime.strptime(date_ref, '%Y-%m-%d') + RelativeDateTime(days=line.days)
				if line.condition == 'end of month':
					next_date += RelativeDateTime(day=-1)
				result.append( (next_date.strftime('%Y-%m-%d'), amt) )
				amount -= amt
		return result
account_payment_term()

class account_payment_term_line(osv.osv):
	_name = "account.payment.term.line"
	_description = "Payment Term Line"
	_columns = {
		'name': fields.char('Line Name', size=32,required=True),
		'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the payment term lines from the lowest sequences to the higher ones"),
		'value': fields.selection([('procent','Procent'),('balance','Balance'),('fixed','Fixed Amount')], 'Value',required=True),
		'value_amount': fields.float('Value Amount'),
		'days': fields.integer('Number of Days',required=True),
		'condition': fields.selection([('net days','Net Days'),('end of month','End of Month')], 'Condition', required=True, help="The payment delay condition id a number of days expressed in 2 ways: net days or end of the month. The 'net days' condition implies that the paiment arrive after 'Number of Days' calendar days. The 'end of the month' condition requires that the paiement arrives before the end of the month that is that is after 'Number of Days' calendar days."),
		'payment_id': fields.many2one('account.payment.term','Payment Term', required=True, select=True),
	}
	_defaults = {
		'value': lambda *a: 'balance',
		'sequence': lambda *a: 5,
		'condition': lambda *a: 'net days',
	}
	_order = "sequence"
account_payment_term_line()


class account_account_type(osv.osv):
	_name = "account.account.type"
	_description = "Account Type"
	_columns = {
		'name': fields.char('Acc. Type Name', size=64, required=True, translate=True),
		'code': fields.char('Code', size=32, required=True),
		'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of account types."),
		'code_from': fields.char('Code From', size=10, help="Gives the range of account code available for this type of account. These fields are given for information and are not used in any constraint."),
		'code_to': fields.char('Code To', size=10, help="Gives the range of account code available for this type of account. These fields are just given for information and are not used in any constraint."),
		'partner_account': fields.boolean('Partner account'),
		'close_method': fields.selection([('none','None'), ('balance','Balance'), ('detail','Detail'),('unreconciled','Unreconciled')], 'Deferral Method', required=True),
	}
	_defaults = {
		'close_method': lambda *a: 'none',
		'sequence': lambda *a: 5,
	}
	_order = "sequence"
account_account_type()

def _code_get(self, cr, uid, context={}):
	acc_type_obj = self.pool.get('account.account.type')
	ids = acc_type_obj.search(cr, uid, [])
	res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context)
	return [(r['code'], r['name']) for r in res]

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------
class account_account(osv.osv):
	_order = "code"
	_name = "account.account"
	_description = "Account"

	def _credit(self, cr, uid, ids, field_name, arg, context={}):
		acc_set = ",".join(map(str, ids))
		cr.execute("SELECT a.id, COALESCE(SUM(l.credit*a.sign),0) FROM account_account a LEFT JOIN account_move_line l ON (a.id=l.account_id) WHERE a.type!='view' AND a.id IN (%s) AND l.active AND l.state<>'draft' GROUP BY a.id" % acc_set)
		res2 = cr.fetchall()
		res = {}
		for id in ids:
			res[id] = 0.0
		for account_id, sum in res2:
			res[account_id] += sum
		return res

	def _debit(self, cr, uid, ids, field_name, arg, context={}):
		acc_set = ",".join(map(str, ids))
		cr.execute("SELECT a.id, COALESCE(SUM(l.debit*a.sign),0) FROM account_account a LEFT JOIN account_move_line l ON (a.id=l.account_id) WHERE a.type!='view' AND a.id IN (%s) and l.active AND l.state<>'draft' GROUP BY a.id" % acc_set)
		res2 = cr.fetchall()
		res = {}
		for id in ids:
			res[id] = 0.0
		for account_id, sum in res2:
			res[account_id] += sum
		return res

	def _balance(self, cr, uid, ids, field_name, arg, context={}):
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		acc_set = ",".join(map(str, ids2))
		cr.execute("SELECT a.id, COALESCE(SUM((l.debit-l.credit)),0) FROM account_account a LEFT JOIN account_move_line l ON (a.id=l.account_id) WHERE a.id IN (%s) and l.active AND l.state<>'draft' GROUP BY a.id" % acc_set)
		res = {}
		for account_id, sum in cr.fetchall():
			res[account_id] = round(sum,2)
		for id in ids:
			ids3 = self.search(cr, uid, [('parent_id', 'child_of', [id])])
			for idx in ids3:
				if idx <> id:
					res.setdefault(id, 0.0)
					res[id] += res.get(idx, 0.0)
		for id in ids:
			res[id] = round(res.get(id,0.0), 2)
		return res

	_columns = {
		'name': fields.char('Name', size=128, required=True, translate=True, select=True),
		'sign': fields.selection([(-1, 'Negative'), (1, 'Positive')], 'Sign', required=True, help='Allows to change the displayed amount of the balance to see positive results instead of negative ones in expenses accounts'),
		'currency_id': fields.many2one('res.currency', 'Currency', required=True),
		'code': fields.char('Code', size=64),
		'type': fields.selection(_code_get, 'Account Type', required=True),
		'parent_id': fields.many2many('account.account', 'account_account_rel', 'child_id', 'parent_id', 'Parents'),
		'child_id': fields.many2many('account.account', 'account_account_rel', 'parent_id', 'child_id', 'Children'),
		'balance': fields.function(_balance, digits=(16,2), method=True, string='Balance'),
		'credit': fields.function(_credit, digits=(16,2), method=True, string='Credit'),
		'debit': fields.function(_debit, digits=(16,2), method=True, string='Debit'),
		'reconcile': fields.boolean('Reconcile', help="Check this account if the user can make a reconciliation of the entries in this account."),
		'shortcut': fields.char('Shortcut', size=12),
		'close_method': fields.selection([('none','None'), ('balance','Balance'), ('detail','Detail'),('unreconciled','Unreconciled')], 'Deferral Method', required=True, help="Tell Tiny ERP how to process the entries of this account when you close a fiscal year. None removes all entries to start with an empty account for the new fiscal year. Balance creates only one entry to keep the balance for the new fiscal year. Detail keeps the detail of all entries of the preceeding years. Unreconciled keeps the detail of unreconciled entries only."),
		'tax_ids': fields.many2many('account.tax', 'account_account_tax_default_rel', 'account_id','tax_id', 'Default Taxes'),
		'company_id': fields.many2one('res.company', 'Company'),

		'active': fields.boolean('Active'),
		'note': fields.text('Note')
	}
	_defaults = {
		'sign': lambda *a: 1,
		'type': lambda *a: 'view',
		'active': lambda *a: True,
		'reconcile': lambda *a: False,
		'close_method': lambda *a: 'balance',
	}
	def _check_recursion(self, cr, uid, ids):
		level = 100
		while len(ids):
			cr.execute('select distinct parent_id from account_account_rel where child_id in ('+','.join(map(str,ids))+')')
			ids = filter(None, map(lambda x:x[0], cr.fetchall()))
			if not level:
				return False
			level -= 1
		return True

	_constraints = [
		(_check_recursion, 'Error ! You can not create recursive accounts.', ['parent_id'])
	]
	def init(self, cr):
		cr.execute("SELECT relname FROM pg_class WHERE relkind='r' AND relname='account_tax'")
		if len(cr.dictfetchall())==0:
			cr.execute("CREATE TABLE account_tax (id SERIAL NOT NULL, perm_id INTEGER, PRIMARY KEY(id))");
			cr.commit()

	def name_search(self, cr, user, name, args=[], operator='ilike', context={}):
		ids = []
		if name:
			ids = self.search(cr, user, [('code','=like',name+"%")]+ args)
			if not ids:
				ids = self.search(cr, user, [('shortcut','=',name)]+ args)
			if not ids:
				ids = self.search(cr, user, [('name',operator,name)]+ args)
		else:
			ids = self.search(cr, user, args)
		return self.name_get(cr, user, ids, context=context)

	def name_get(self, cr, uid, ids, context={}):
		if not len(ids):
			return []
		reads = self.read(cr, uid, ids, ['name','code'], context)
		res = []
		for record in reads:
			name = record['name']
			if record['code']:
				name = record['code']+' - '+name
			res.append((record['id'],name ))
		return res
account_account()

class account_journal_view(osv.osv):
	_name = "account.journal.view"
	_description = "Journal View"
	_columns = {
		'name': fields.char('Journal View', size=64, required=True),
		'columns_id': fields.one2many('account.journal.column', 'view_id', 'Columns')
	}
	_order = "name"
account_journal_view()


class account_journal_column(osv.osv):
	def _col_get(self, cr, user, context={}):
		result = []
		cols = self.pool.get('account.move.line')._columns
		for col in cols:
			result.append( (col, cols[col].string) )
		result.sort()
		return result
	_name = "account.journal.column"
	_description = "Journal Column"
	_columns = {
		'name': fields.char('Column Name', size=64, required=True),
		'field': fields.selection(_col_get, 'Field Name', method=True, required=True, size=32),
		'view_id': fields.many2one('account.journal.view', 'Journal View', select=True),
		'sequence': fields.integer('Sequence'),
		'required': fields.boolean('Required'),
		'readonly': fields.boolean('Readonly'),
	}
	_order = "sequence"
account_journal_column()


class account_journal(osv.osv):
	_name = "account.journal"
	_description = "Journal"
	_columns = {
		'name': fields.char('Journal Name', size=64, required=True),
		'code': fields.char('Code', size=9),
		'type': fields.selection([('sale','Sale'), ('purchase','Purchase'), ('cash','Cash'), ('general','General'), ('situation','Situation')], 'Type', size=32, required=True),
		'type_control_ids': fields.many2many('account.account.type', 'account_journal_type_rel', 'journal_id','type_id', 'Type Controls', domain=[('code','<>','view')]),
		'active': fields.boolean('Active'),
		'view_id': fields.many2one('account.journal.view', 'View', required=True, help="Gives the view used when writing or browsing entries in this journal. The view tell Tiny ERP which fields should be visible, required or readonly and in which order. You can create your own view for a faster encoding in each journal."),
		'default_credit_account_id': fields.many2one('account.account', 'Default Credit Account'),
		'default_debit_account_id': fields.many2one('account.account', 'Default Debit Account'),
		'centralisation': fields.boolean('Centralisation', help="Use a centralisation journal if you want that each entry doesn't create a counterpart but share the same counterpart for each entry of this journal."),
		'update_posted': fields.boolean('Allow Cancelling Entries'),
		'sequence_id': fields.many2one('ir.sequence', 'Entry Sequence', help="The sequence gives the display order for a list of journals"),
		'user_id': fields.many2one('res.users', 'User', help="The responsible user of this journal"),
		'groups_id': fields.many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', 'Groups'),
	}
	_defaults = {
		'active': lambda *a: 1,
		'user_id': lambda self,cr,uid,context: uid,
	}
	def create(self, cr, uid, vals, context={}):
		journal_id = super(osv.osv, self).create(cr, uid, vals, context)
#		journal_name = self.browse(cr, uid, [journal_id])[0].code
#		periods = self.pool.get('account.period')
#		ids = periods.search(cr, uid, [('date_stop','>=',time.strftime('%Y-%m-%d'))])
#		for period in periods.browse(cr, uid, ids):
#			self.pool.get('account.journal.period').create(cr, uid, {
#				'name': (journal_name or '')+':'+(period.code or ''),
#				'journal_id': journal_id,
#				'period_id': period.id
#			})
		return journal_id
	def name_search(self, cr, user, name, args=[], operator='ilike', context={}):
		ids = []
		if name:
			ids = self.search(cr, user, [('code','ilike',name)]+ args)
		if not ids:
			ids = self.search(cr, user, [('name',operator,name)]+ args)
		return self.name_get(cr, user, ids, context=context)
account_journal()

class account_bank(osv.osv):
	_name = "account.bank"
	_description = "Banks"
	_columns = {
		'name': fields.char('Bank Name', size=64, required=True),
		'code': fields.char('Code', size=6),
		'partner_id': fields.many2one('res.partner', 'Bank Partner', help="The link to the partner that represent this bank. The partner contains all information about contacts, phones, applied taxes, eso."),
		'bank_account_ids': fields.one2many('account.bank.account', 'bank_id', 'Bank Accounts'),
		'note': fields.text('Notes'),
	}
	_order = "code"
account_bank()

class account_bank_account(osv.osv):
	_name = "account.bank.account"
	_description = "Bank Accounts"
	_columns = {
		'name': fields.char('Bank Account', size=64, required=True),
		'code': fields.char('Code', size=6),
		'iban': fields.char('IBAN', size=24),
		'swift': fields.char('Swift Code', size=24),
		'currency_id': fields.many2one('res.currency', 'Currency', required=True),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True),
		'account_id': fields.many2one('account.account', 'General Account', required=True, select=True),
		'bank_id': fields.many2one('account.bank', 'Bank'),
	}
	_order = "code"
account_bank_account()


class account_fiscalyear(osv.osv):
	_name = "account.fiscalyear"
	_description = "Fiscal Year"
	_columns = {
		'name': fields.char('Fiscal Year', size=64, required=True),
		'code': fields.char('Code', size=6, required=True),
		'company_id': fields.many2one('res.company', 'Company'),
		'date_start': fields.date('Start date', required=True),
		'date_stop': fields.date('End date', required=True),
		'period_ids': fields.one2many('account.period', 'fiscalyear_id', 'Periods'),
		'state': fields.selection([('draft','Draft'), ('done','Done')], 'State', redonly=True)
	}
	_defaults = {
		'state': lambda *a: 'draft',
	}
	_order = "code"
	def create_period3(self,cr, uid, ids, context={}):
		return self.create_period(cr, uid, ids, context, 3)

	def create_period(self,cr, uid, ids, context={}, interval=1):
		for fy in self.browse(cr, uid, ids, context):
			dt = fy.date_start
			ds = mx.DateTime.strptime(fy.date_start, '%Y-%m-%d')
			while ds.strftime('%Y-%m-%d')<fy.date_stop:
				de = ds + RelativeDateTime(months=interval, days=-1)
				self.pool.get('account.period').create(cr, uid, {
					'name': ds.strftime('%d/%m') + ' - '+de.strftime('%d/%m'),
					'code': ds.strftime('%d/%m') + '-'+de.strftime('%d/%m'),
					'date_start': ds.strftime('%Y-%m-%d'),
					'date_stop': de.strftime('%Y-%m-%d'),
					'fiscalyear_id': fy.id,
				})
				ds = ds + RelativeDateTime(months=interval)
		return True
account_fiscalyear()

class account_period(osv.osv):
	_name = "account.period"
	_description = "Account period"
	_columns = {
		'name': fields.char('Period Name', size=64, required=True),
		'code': fields.char('Code', size=12),
		'date_start': fields.date('Start of period', required=True, states={'done':[('readonly',True)]}),
		'date_stop': fields.date('End of period', required=True, states={'done':[('readonly',True)]}),
		'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, states={'done':[('readonly',True)]}, select=True),
		'state': fields.selection([('draft','Draft'), ('done','Done')], 'State', readonly=True)
	}
	_defaults = {
		'state': lambda *a: 'draft',
	}
	_order = "date_start"

	def find(self, cr, uid, dt=None, context={}):
		if not dt:
			dt = time.strftime('%Y-%m-%d')
#CHECKME: shouldn't we check the state of the period?
		ids = self.search(cr, uid, [('date_start','<=',dt),('date_stop','>=',dt)])
		if not ids:
			raise osv.except_osv('Error !', 'No period defined for this date !\nPlease create a fiscal year.')
		return ids
account_period()

class account_journal_period(osv.osv):
	_name = "account.journal.period"
	_description = "Journal - Period"
	def _icon_get(self, cr, uid, ids, field_name, arg=None, context={}):
		result = {}.fromkeys(ids, 'STOCK_NEW')
		for r in self.read(cr, uid, ids, ['state']):
			result[r['id']] = {
				'draft': 'STOCK_NEW',
				'printed': 'STOCK_PRINT_PREVIEW',
				'done': 'STOCK_DIALOG_AUTHENTICATION',
			}.get(r['state'], 'STOCK_NEW')
		return result
	_columns = {
		'name': fields.char('Journal-Period Name', size=64, required=True),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True, ondelete="cascade"),
		'period_id': fields.many2one('account.period', 'Period', required=True, ondelete="cascade"),
		'icon': fields.function(_icon_get, method=True, string='Icon'),
		'active': fields.boolean('Active', required=True),
		'state': fields.selection([('draft','Draft'), ('printed','Printed'), ('done','Done')], 'State', required=True, readonly=True)
	}
	def _check(self, cr, uid, ids, context={}):
		for obj in self.browse(cr, uid, ids, context):
			cr.execute('select * from account_move_line where journal_id=%d and period_id=%d limit 1', (obj.journal_id.id, obj.period_id.id))
			res = cr.fetchall()
			if res:
				raise osv.except_osv('Error !', 'You can not modify/delete a journal with entries for this period !')
		return True

	def write(self, cr, uid, ids, vals, context={}):
		self._check(cr, uid, ids, context)
		return super(account_journal_period, self).write(cr, uid, ids, vals, context)

	def unlink(self, cr, uid, ids, context={}):
		self._check(cr, uid, ids, context)
		return super(account_journal_period, self).unlink(cr, uid, ids, context)

	_defaults = {
		'state': lambda *a: 'draft',
		'active': lambda *a: True,
	}
	_order = "period_id"
account_journal_period()

#----------------------------------------------------------
# Entries
#----------------------------------------------------------
class account_move(osv.osv):
	_name = "account.move"
	_description = "Account Entry"

	def _get_period(self, cr, uid, context):
		periods = self.pool.get('account.period').find(cr, uid)
		if periods:
			return periods[0]
		else:
			return False
	_columns = {
		'name': fields.char('Entry Name', size=64, required=True),
		'ref': fields.char('Ref', size=64),
		'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True, states={'posted':[('readonly',True)]}, relate=True),
		'state': fields.selection([('draft','Draft'), ('posted','Posted')], 'State', required=True, readonly=True),
		'line_id': fields.one2many('account.move.line', 'move_id', 'Entries', states={'posted':[('readonly',True)]}),
	}
	_defaults = {
		'state': lambda *a: 'draft',
		'period_id': _get_period,
	}
	def button_validate(self, cr, uid, ids, context={}):
		if self.validate(cr, uid, ids, context) and len(ids):
			cr.execute('update account_move set state=%s where id in ('+','.join(map(str,ids))+')', ('posted',))
		else:
			cr.execute('update account_move set state=%s where id in ('+','.join(map(str,ids))+')', ('draft',))
			cr.commit()
			raise osv.except_osv('Integrity Error !', 'You can not validate a non balanced entry !')
		return True

	def button_cancel(self, cr, uid, ids, context={}):
		for line in self.browse(cr, uid, ids, context):
			if not line.journal_id.update_posted:
				raise osv.except_osv('Error !', 'You can not modify a posted entry of this journal !')
		if len(ids):
			cr.execute('update account_move set state=%s where id in ('+','.join(map(str,ids))+')', ('draft',))
		return True

	def write(self, cr, uid, ids, vals, context={}):
		c = context.copy()
		c['novalidate'] = True
		result = super(osv.osv, self).write(cr, uid, ids, vals, c)
		self.validate(cr, uid, ids, context)
		return result

	#
	# TODO: Check if period is closed !
	#
	def create(self, cr, uid, vals, context={}):
		if 'line_id' in vals:
			if 'journal_id' in vals:
				for l in vals['line_id']:
					if not l[0]:
						l[2]['journal_id'] = vals['journal_id']
				context['journal_id'] = vals['journal_id']
			if 'period_id' in vals:
				for l in vals['line_id']:
					if not l[0]:
						l[2]['period_id'] = vals['period_id']
				context['period_id'] = vals['period_id']
			else:
				default_period = self._get_period(cr, uid, context)
				for l in vals['line_id']:
					if not l[0]:
						l[2]['period_id'] = default_period
				context['period_id'] = default_period

		if 'line_id' in vals:
			c = context.copy()
			c['novalidate'] = True
			result = super(account_move, self).create(cr, uid, vals, c)
			self.validate(cr, uid, [result], context)
		else:
			result = super(account_move, self).create(cr, uid, vals, context)
		return result

	def unlink(self, cr, uid, ids, context={}, check=True):
		toremove = []
		for move in self.browse(cr, uid, ids, context):
			line_ids = map(lambda x: x.id, move.line_id)
			context['journal_id'] = move.journal_id.id
			context['period_id'] = move.period_id.id
			self.pool.get('account.move.line')._update_check(cr, uid, line_ids, context)
			toremove.append(move.id)
		result = super(account_move, self).unlink(cr, uid, toremove, context)
		return result

	def _compute_balance(self, cr, uid, id, context={}):
		move = self.browse(cr, uid, [id])[0]
		amount = 0
		for line in move.line_id:
			amount+= (line.debit - line.credit)
		return amount

	def _centralise(self, cr, uid, move, mode):
		if mode=='credit':
			account_id = move.journal_id.default_debit_account_id.id
			mode2 = 'debit'
		else:
			account_id = move.journal_id.default_credit_account_id.id
			mode2 = 'credit'

		# find the first line of this move with the current mode 
		# or create it if it doesn't exist
		cr.execute('select id from account_move_line where move_id=%d and centralisation=%s limit 1', (move.id, mode))
		res = cr.fetchone()
		if res:
			line_id = res[0]
		else:
			line_id = self.pool.get('account.move.line').create(cr, uid, {
				'name': 'Centralisation '+mode,
				'centralisation': mode,
				'account_id': account_id,
				'move_id': move.id,
				'journal_id': move.journal_id.id,
				'period_id': move.period_id.id,
				'date': move.period_id.date_stop,
				'debit': 0.0,
				'credit': 0.0,
			}, {'journal_id': move.journal_id.id, 'period_id': move.period_id.id})

		# find the first line of this move with the other mode
		# so that we can exclude it from our calculation
		cr.execute('select id from account_move_line where move_id=%d and centralisation=%s limit 1', (move.id, mode2))
		res = cr.fetchone()
		if res:
			line_id2 = res[0]
		else:
			line_id2 = 0

		cr.execute('select sum('+mode+') from account_move_line where move_id=%d and id<>%d', (move.id, line_id2))
		result = cr.fetchone()[0] or 0.0
		cr.execute('update account_move_line set '+mode2+'=%f where id=%d', (result, line_id))
		return True

	#
	# Validate a balanced move. If it is a centralised journal, create a move.
	#
	def validate(self, cr, uid, ids, context={}):
		ok = True
		for move in self.browse(cr, uid, ids, context):
			journal = move.journal_id
			amount = 0
			line_ids = []
			line_draft_ids = []
			for line in move.line_id:
				amount += line.debit - line.credit
				line_ids.append(line.id)
				if line.state=='draft':
					line_draft_ids.append(line.id)
			if abs(amount) < 0.0001:
				if not len(line_draft_ids):
					continue
				self.pool.get('account.move.line').write(cr, uid, line_draft_ids, {
					'journal_id': move.journal_id.id,
					'period_id': move.period_id.id,
					'state': 'valid'
				}, context, check=False)
				todo = []
				account = {}
				account2 = {}
				field_base = ''
				if journal.type not in ('purchase','sale'):
					continue
				if journal.type=='purchase':
					field_base='ref_'

				for line in move.line_id:
					if line.account_id.tax_ids:
						code = amount = False
						for tax in line.account_id.tax_ids:
							if tax.tax_code_id:
								acc = (line.debit >0) and tax.account_paid_id.id or tax.account_collected_id.id
								account[acc] = (getattr(tax,field_base+'tax_code_id').id, getattr(tax,field_base+'tax_sign'))
								account2[(acc,getattr(tax,field_base+'tax_code_id').id)] = (getattr(tax,field_base+'tax_code_id').id, getattr(tax,field_base+'tax_sign'))
								code = getattr(tax,field_base+'base_code_id').id
								amount = getattr(tax, field_base+'base_sign') * (line.debit + line.credit)
								break
						if code: 
							self.pool.get('account.move.line').write(cr, uid, [line.id], {
								'tax_code_id': code,
								'tax_amount': amount
							}, context, check=False)
					else:
						todo.append(line)
				for line in todo:
					code = amount = 0
					key = (line.account_id.id,line.tax_code_id.id)
					if key in account2:
						code = account2[key][0]
						amount = account2[key][1] * (line.debit + line.credit)
					elif line.account_id.id in account:
						code = account[line.account_id.id][0]
						amount = account[line.account_id.id][1] * (line.debit + line.credit)
					if code or amount:
						self.pool.get('account.move.line').write(cr, uid, [line.id], {
							'tax_code_id': code,
							'tax_amount': amount
						}, context, check=False)
				#
				# Compute VAT
				#
				continue
			if journal.centralisation:
				self._centralise(cr, uid, move, 'debit')
				self._centralise(cr, uid, move, 'credit')
				self.pool.get('account.move.line').write(cr, uid, line_draft_ids, {
					'state': 'valid'
				}, context, check=False)
				continue
			else:
				self.pool.get('account.move.line').write(cr, uid, line_ids, {
					'journal_id': move.journal_id.id,
					'period_id': move.period_id.id,
					#'tax_code_id': False,
					'tax_amount': False,
					'state': 'draft'
				}, context, check=False)
				ok = False
		return ok
account_move()

class account_move_reconcile(osv.osv):
	_name = "account.move.reconcile"
	_description = "Account Reconciliation"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'type': fields.char('Type', size=16, required=True),
		'line_id': fields.one2many('account.move.line', 'reconcile_id', 'Entry lines'),
	}
	_defaults = {
		'name': lambda *a: 'reconcile '+time.strftime('%Y-%m-%d')
	}
account_move_reconcile()

#
# use a sequence for names ?
# 
class account_bank_statement(osv.osv):
	def _default_journal_id(self, cr, uid, context={}):
		if context.get('journal_id', False):
			return context['journal_id']
		if  context.get('journal_id', False):
			# TODO: write this
			return False
		return False

	def _default_balance_start(self, cr, uid, context={}):
		cr.execute('select id from account_bank_statement where journal_id=%d order by date desc limit 1', (1,))
		res = cr.fetchone()
		if res:
			return self.browse(cr, uid, [res[0]], context)[0].balance_end
		return 0.0

	def _end_balance(self, cr, uid, ids, prop, unknow_none, unknow_dict):
		res = {}
		statements = self.browse(cr, uid, ids)
		for statement in statements:
			res[statement.id] = statement.balance_start
			for line in statement.line_ids:
				res[statement.id] += line.amount
		for r in res:
			res[r] = round(res[r], 2)
		return res

	def _get_period(self, cr, uid, context={}):
		periods = self.pool.get('account.period').find(cr, uid)
		if periods:
			return periods[0]
		else:
			return False

	_order = "date desc"
	_name = "account.bank.statement"
	_description = "Bank Statement"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'date': fields.date('Date', required=True, states={'confirm':[('readonly',True)]}),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True, states={'confirm':[('readonly',True)]}, domain=[('type','=','cash')], relate=True),
		'period_id': fields.many2one('account.period', 'Period', required=True, states={'confirm':[('readonly',True)]}),
		'balance_start': fields.float('Starting Balance', digits=(16,2), states={'confirm':[('readonly',True)]}),
		'balance_end_real': fields.float('Ending Balance', digits=(16,2), states={'confirm':[('readonly',True)]}),
		'balance_end': fields.function(_end_balance, method=True, string='Balance'),
		'line_ids': fields.one2many('account.bank.statement.line', 'statement_id', 'Statement lines', states={'confirm':[('readonly',True)]}),
		'move_line_ids': fields.one2many('account.move.line', 'statement_id', 'Entry lines', states={'confirm':[('readonly',True)]}),
		'state': fields.selection([('draft','Draft'),('confirm','Confirm')], 'State', required=True, states={'confirm':[('readonly',True)]}, readonly="1"),
	}
	_defaults = {
		'name': lambda self,cr,uid,context={}: self.pool.get('ir.sequence').get(cr, uid, 'account.bank.statement'),
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'state': lambda *a: 'draft',
		'balance_start': _default_balance_start,
		'journal_id': _default_journal_id,
		'period_id': _get_period,
	}
	def button_confirm(self, cr, uid, ids, context={}):
		done = []
		for st in self.browse(cr, uid, ids, context):
			if not st.state=='draft':
				continue
			if not (abs(st.balance_end - st.balance_end_real) < 0.0001):
				raise osv.except_osv('Error !', 'The statement balance is incorrect !\nCheck that the ending balance equals the computed one.')
			if (not st.journal_id.default_credit_account_id) or (not st.journal_id.default_debit_account_id):
				raise osv.except_osv('Configration Error !', 'Please verify that an account is defined in the journal.')
			for move in st.line_ids:
				if not move.amount:
					continue
				self.pool.get('account.move.line').create(cr, uid, {
					'name': move.name,
					'date': move.date,
					'partner_id': ((move.partner_id) and move.partner_id.id) or False,
					'account_id': (move.account_id) and move.account_id.id,
					'credit': ((move.amount>0) and move.amount) or 0.0,
					'debit': ((move.amount<0) and -move.amount) or 0.0,
					'statement_id': st.id,
					'journal_id': st.journal_id.id,
					'period_id': st.period_id.id,
				}, context=context)
				if not st.journal_id.centralisation:
					c = context.copy()
					c['journal_id'] = st.journal_id.id
					c['period_id'] = st.period_id.id
					fields = ['move_id','name','date','partner_id','account_id','credit','debit']
					default = self.pool.get('account.move.line').default_get(cr, uid, fields, context=c)
					default.update({
						'statement_id': st.id,
						'journal_id': st.journal_id.id,
						'period_id': st.period_id.id,
					})
					self.pool.get('account.move.line').create(cr, uid, default, context=context)
			done.append(st.id)
		self.write(cr, uid, done, {'state':'confirm'}, context=context)
		return True
	def button_cancel(self, cr, uid, ids, context={}):
		done = []
		for st in self.browse(cr, uid, ids, context):
			if st.state=='draft':
				continue
			ids = [x.move_id.id for x in st.move_line_ids]
			self.pool.get('account.move').unlink(cr, uid, ids, context)
			done.append(st.id)
		self.write(cr, uid, done, {'state':'draft'}, context=context)
		return True
	def onchange_journal_id(self, cr, uid, id, journal_id, context={}):
		if not journal_id:
			return {}
		cr.execute('select balance_end_real from account_bank_statement where journal_id=%d order by date desc limit 1', (journal_id,))
		res = cr.fetchone()
		if res:
			return {'value': {'balance_start': res[0] or 0.0}}
		return {}
account_bank_statement()

class account_bank_statement_line(osv.osv):
	def onchange_partner_id(self, cr, uid, id, partner_id, type, context={}):
		if not partner_id:
			return {}
		part = self.pool.get('res.partner').browse(cr, uid, partner_id, context)
		if type=='supplier':
			account_id = part.property_account_payable[0]
		else:
			account_id =  part.property_account_receivable[0]
		cr.execute('select sum(debit-credit) from account_move_line where (reconcile_id is null) and partner_id=%d and account_id=%d', (partner_id, account_id))
		balance = cr.fetchone()[0] or 0.0
		val = {'amount': balance, 'account_id':account_id}
		return {'value':val}
	_order = "date,name desc"
	_name = "account.bank.statement.line"
	_description = "Bank Statement Line"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'date': fields.date('Date'),
		'amount': fields.float('Amount'),
		'type': fields.selection([('supplier','Supplier'),('customer','Customer'),('general','General')], 'Type', required=True),
		'partner_id': fields.many2one('res.partner', 'Partner'),
		'account_id': fields.many2one('account.account','Account', required=True),
		'statement_id': fields.many2one('account.bank.statement', 'Statement', select=True),
	}
	_defaults = {
		'name': lambda self,cr,uid,context={}: self.pool.get('ir.sequence').get(cr, uid, 'account.bank.statement.line'),
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'type': lambda *a: 'general',
	}
account_bank_statement_line()


#----------------------------------------------------------
# Tax
#----------------------------------------------------------
"""
a documenter 
child_depend: la taxe depend des taxes filles
"""
class account_tax_code(osv.osv):
	"""
	A code for the tax object.

	This code is used for some tax declarations.
	"""
	def _sum(self, cr, uid, ids, prop, unknow_none, unknow_dict, where =''):
		ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
		acc_set = ",".join(map(str, ids2))
		cr.execute('SELECT tax_code_id,sum(tax_amount) FROM account_move_line WHERE tax_code_id in ('+acc_set+') '+where+' GROUP BY tax_code_id')
		res=dict(cr.fetchall())
		for id in ids:
			ids3 = self.search(cr, uid, [('parent_id', 'child_of', [id])])
			for idx in ids3:
				if idx <> id:
					res.setdefault(id, 0.0)
					res[id] += res.get(idx, 0.0)
		for id in ids:
			res[id] = round(res.get(id,0.0), 2)
		return res

	def _sum_period(self, cr, uid, ids, prop, unknow_none, context={}):
		if not 'period_id' in context:
			period_id = self.pool.get('account.period').find(cr, uid)
			if not len(period_id):
				return dict.fromkeys(ids, 0.0)
			period_id = period_id[0]
		else:
			period_id = context['period_id']
		return self._sum(cr, uid, ids, prop, unknow_none, context, where=' and period_id='+str(period_id))

	_name = 'account.tax.code'
	_description = 'Tax Code'
	_columns = {
		'name': fields.char('Tax Case Name', size=64, required=True),
		'code': fields.char('Case Code', size=16),
		'info': fields.text('Description'),
		'sum': fields.function(_sum, method=True, string="Year Sum"),
		'sum_period': fields.function(_sum_period, method=True, string="Period Sum"),
		'parent_id': fields.many2one('account.tax.code', 'Parent Code', select=True),
		'child_ids': fields.one2many('account.tax.code', 'parent_id', 'Childs Codes'),
		'line_ids': fields.one2many('account.move.line', 'tax_code_id', 'Lines')
	}
account_tax_code()

class account_move_line(osv.osv):
	_name = "account.move.line"
	_description = "Entry lines"

	def default_get(self, cr, uid, fields, context={}):
		data = self._default_get(cr, uid, fields, context)
		for f in data.keys():
			if f not in fields:
				del data[f]
		return data

	def _default_get(self, cr, uid, fields, context={}):
		# Compute simple values
		data = super(account_move_line, self).default_get(cr, uid, fields, context)

		# Compute the current move
		move_id = False
		partner_id = False
		statement_acc_id = False
		if context.get('journal_id',False) and context.get('period_id',False):
			cr.execute('select move_id \
				from \
					account_move_line \
				where \
					journal_id=%d and period_id=%d and create_uid=%d and state=%s \
				order by id desc limit 1', (context['journal_id'], context['period_id'], uid, 'draft'))
			res = cr.fetchone()
			move_id = (res and res[0]) or False
			cr.execute('select date  \
				from \
					account_move_line \
				where \
					journal_id=%d and period_id=%d and create_uid=%d order by id desc', (context['journal_id'], context['period_id'], uid))
			res = cr.fetchone()
			data['date'] = res and res[0] or time.strftime('%Y-%m-%d')
			cr.execute('select statement_id, account_id  \
				from \
					account_move_line \
				where \
					journal_id=%d and period_id=%d and statement_id is not null and create_uid=%d order by id desc', (context['journal_id'], context['period_id'], uid))
			res = cr.fetchone()
			statement_id = res and res[0] or False
			statement_acc_id = res and res[1]

		if not move_id:
			return data

		data['move_id'] = move_id

		total = 0
		taxes = {}
		move = self.pool.get('account.move').browse(cr, uid, move_id, context)
		for l in move.line_id:
			partner_id = partner_id or l.partner_id.id
			total += (l.debit - l.credit)
			for tax in l.account_id.tax_ids:
				acc = (l.debit >0) and tax.account_paid_id.id or tax.account_collected_id.id
				taxes.setdefault((acc,tax.tax_code_id.id), False)
			taxes[(l.account_id.id,l.tax_code_id.id)] = True
			data.setdefault('name', l.name)

		data['partner_id'] = partner_id

		print taxes
		for t in taxes:
			if not taxes[t] and t[0]:
				s=0
				for l in move.line_id:
					for tax in l.account_id.tax_ids:
						taxes = self.pool.get('account.tax').compute(cr, uid, [tax.id], l.debit or l.credit, 1, False)
						key = (l.debit and 'account_paid_id') or 'account_collected_id'
						for t2 in taxes:
							if (t2[key] == t[0]) and (tax.tax_code_id.id==t[1]):
								if l.debit:
									s += t2['amount']
								else:
									s -= t2['amount']
				data['debit'] = s>0  and s or 0.0
				data['credit'] = s<0  and -s or 0.0

				data['tax_code_id'] = t[1]

				data['account_id'] = t[0]

				#
				# Compute line for tax T
				#
				return data

		#
		# Compute latest line
		#
		data['credit'] = total>0 and total
		data['debit'] = total<0 and -total
		if total>=0:
			data['account_id'] = move.journal_id.default_credit_account_id.id or False
		else:
			data['account_id'] = move.journal_id.default_debit_account_id.id or False
		if data['account_id']:
			account = self.pool.get('account.account').browse(cr, uid, data['account_id'])
			data['tax_code_id'] = self._default_get_tax(cr, uid, account )
		return data

	def _default_get_tax(self, cr, uid, account, debit=0, credit=0, context={}):
		if account.tax_ids:
			return account.tax_ids[0].base_code_id.id
		return False

	def _on_create_write(self, cr, uid, id, context={}):
		ml = self.browse(cr, uid, id, context)
		return map(lambda x: x.id, ml.move_id.line_id)

	def _balance(self, cr, uid, ids, prop, unknow_none, unknow_dict):
		res={}
		# TODO group the foreach in sql
		for id in ids:
			cr.execute('SELECT date,account_id FROM account_move_line WHERE id=%d', (id,))
			dt, acc = cr.fetchone()
			cr.execute('SELECT SUM(debit-credit) FROM account_move_line WHERE account_id=%d AND (date<%s OR (date=%s AND id<=%d)) and active', (acc,dt,dt,id))
			res[id] = cr.fetchone()[0]
		return res

	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'quantity': fields.float('Quantity', digits=(16,2), help="The optionnal quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very usefull for some reports."),
		'debit': fields.float('Debit', digits=(16,2), states={'reconciled':[('readonly',True)]}),
		'credit': fields.float('Credit', digits=(16,2), states={'reconciled':[('readonly',True)]}),
		'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade", states={'reconciled':[('readonly',True)]}, domain=[('type','<>','view')]),

		'move_id': fields.many2one('account.move', 'Entry', required=True, ondelete="cascade", states={'reconciled':[('readonly',True)]}, help="The entry of this entry line.", select=True),

		'ref': fields.char('Ref.', size=32),
		'statement_id': fields.many2one('account.bank.statement', 'Statement', help="The bank statement used for bank reconciliation", select=True),
		'reconcile_id': fields.many2one('account.move.reconcile', 'Reconcile', readonly=True, ondelete='set null', select=True),
		'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optionnal other currency if it is a multi-currency entry."),
		'currency_id': fields.many2one('res.currency', 'Currency', help="The optionnal other currency if it is a multi-currency entry."),

		'period_id': fields.many2one('account.period', 'Period', required=True),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True, relate=True),
		'blocked': fields.boolean('Litigation', help="You can check this box to mark the entry line as a litigation with the associated partner"),

		'partner_id': fields.many2one('res.partner', 'Partner Ref.', states={'reconciled':[('readonly',True)]}),
		'date_maturity': fields.date('Maturity date', states={'reconciled':[('readonly',True)]}, help="This field is used for payable and receivable entries. You can put the limit date for the payment of this entry line."),
		'date': fields.date('Effective date', required=True),
		'date_created': fields.date('Creation date'),
		'analytic_lines': fields.one2many('account.analytic.line', 'move_id', 'Analytic lines'),
		'centralisation': fields.selection([('normal','Normal'),('credit','Credit Centralisation'),('debit','Debit Centralisation')], 'Centralisation', size=6),
		'balance': fields.function(_balance, method=True, string='Balance'),
		'active': fields.boolean('Active'),
		'state': fields.selection([('draft','Draft'), ('valid','Valid'), ('reconciled','Reconciled')], 'State', readonly=True),
		'tax_code_id': fields.many2one('account.tax.code', 'Tax Account'),
		'tax_amount': fields.float('Tax/Base Amount', digits=(16,2), select=True),
	}
	_defaults = {
		'blocked': lambda *a: False,
		'active': lambda *a: True,
		'centralisation': lambda *a: 'normal',
		'date_created': lambda *a: time.strftime('%Y-%m-%d'),
		'state': lambda *a: 'draft',
		'journal_id': lambda self, cr, uid, c: c.get('journal_id', False),
		'period_id': lambda self, cr, uid, c: c.get('period_id', False),
	}
	_order = "date desc,id desc"
	_sql_constraints = [
		('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
		('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
	]
	def onchange_partner_id(self, cr, uid, ids, move_id, partner_id, account_id=None, debit=0, credit=0, journal=False):
		if (not partner_id) or account_id:
			return {}
		part = self.pool.get('res.partner').browse(cr, uid, partner_id)
		id1 = part.property_account_payable[0]
		id2 =  part.property_account_receivable[0]
		cr.execute('select sum(debit-credit) from account_move_line where (reconcile_id is null) and partner_id=%d and account_id=%d', (partner_id, id2))
		balance = cr.fetchone()[0] or 0.0
		val = {}
		if (not debit) and (not credit):
			if abs(balance)>0.01:
				val['credit'] = ((balance>0) and balance) or 0
				val['debit'] = ((balance<0) and -balance) or 0
				val['account_id'] = id2
			else:
				cr.execute('select sum(debit-credit) from account_move_line where (reconcile_id is null) and partner_id=%d and account_id=%d', (partner_id, id1))
				balance = cr.fetchone()[0] or 0.0
				val['credit'] = ((balance>0) and balance) or 0
				val['debit'] = ((balance<0) and -balance) or 0
				val['account_id'] = id1
		else:
			val['account_id'] =  (debit>0) and id2 or id1
		if journal:
			jt = self.pool.get('account.journal').browse(cr, uid, journal).type
			if jt=='sale':
				val['account_id'] =  id2
			elif jt=='purchase':
				val['account_id'] =  id1
		return {'value':val}

	#
	# type: the type if reconciliation (no logic behind this field, for infà)
	#
	# writeoff; entry generated for the difference between the lines
	#

	def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context={}):
		id_set = ','.join(map(str, ids))
		lines = self.read(cr, uid, ids, context=context)
		unrec_lines = filter(lambda x: not x['reconcile_id'], lines)
		credit = debit = 0
		account_id = False
		partner_id = False
		for line in unrec_lines:
			credit += line['credit']
			debit += line['debit']
			account_id = line['account_id'][0]
			partner_id = (line['partner_id'] and line['partner_id'][0]) or False
		writeoff = debit - credit
		date = time.strftime('%Y-%m-%d')

		cr.execute('SELECT account_id,reconcile_id FROM account_move_line WHERE id IN ('+id_set+') GROUP BY account_id,reconcile_id')
		r = cr.fetchall()
#TODO: move this check to a constraint in the account_move_reconcile object
		if len(r) != 1:
			raise 'Entries are not of the same account !'
		if r[0][1] != None:
			raise 'Some entries are already reconciled !'
		if writeoff != 0:
			if not writeoff_acc_id:
				raise osv.except_osv('Warning', 'You have to provide an account for the write off entry !')
			if writeoff > 0:
				debit = writeoff
				credit = 0.0
				self_credit = writeoff
				self_debit = 0.0
			else:
				debit = 0.0
				credit = -writeoff
				self_credit = 0.0
				self_debit = -writeoff

			writeoff_lines = [
				(0, 0, {'name':'Write-Off', 'debit':self_debit, 'credit':self_credit, 'account_id':account_id, 'date':date, 'partner_id':partner_id}),
				(0, 0, {'name':'Write-Off', 'debit':debit, 'credit':credit, 'account_id':writeoff_acc_id, 'date':date, 'partner_id':partner_id})
			]

			name = 'Write-Off'
			if writeoff_journal_id:
				journal = self.pool.get('account.journal').browse(cr, uid, writeoff_journal_id)
				if journal.sequence_id:
					name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id)

			writeoff_move_id = self.pool.get('account.move').create(cr, uid, {
				'name': name,
				'period_id': writeoff_period_id,
				'journal_id': writeoff_journal_id,

				'state': 'draft',
				'line_id': writeoff_lines
			})

			writeoff_line_ids = self.search(cr, uid, [('move_id', '=', writeoff_move_id), ('account_id', '=', account_id)])
			ids += writeoff_line_ids
			
		self.write(cr, uid, ids, {'state': 'reconciled'}, update_check=False)
		r_id = self.pool.get('account.move.reconcile').create(cr, uid, {
			'name': date, 
			'type': type, 
			'line_id': map(lambda x: (4,x,False), ids)
		})
		# the id of the move.reconcile is written in the move.line (self) by the create method above 
		# because of the way the line_id are defined: (4, x, False)
		wf_service = netsvc.LocalService("workflow")
		for id in ids:
			wf_service.trg_trigger(uid, 'account.move.line', id, cr)
		return r_id

	def view_header_get(self, cr, user, view_id, view_type, context):
		if (not context.get('journal_id', False)) or (not context.get('period_id', False)):
			return False
		cr.execute('select code from account_journal where id=%d', (context['journal_id'],))
		j = cr.fetchone()[0] or ''
		cr.execute('select code from account_period where id=%d', (context['period_id'],))
		p = cr.fetchone()[0] or ''
		if j or p:
			return j+':'+p
		return 'Journal'

	def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False):
		result = super(osv.osv, self).fields_view_get(cr, uid, view_id,view_type,context)
		if view_type=='tree' and 'journal_id' in context:
			title = self.view_header_get(cr, uid, view_id, view_type, context)
			journal = self.pool.get('account.journal').browse(cr, uid, context['journal_id'])

			# if the journal view has a state field, color lines depending on
			# its value
			state = ''
			for field in journal.view_id.columns_id:
				if field.field=='state':
					state = ' colors="red:state==\'draft\'"'

			#xml = '''<?xml version="1.0"?>\n<tree string="%s" editable="top" refresh="5"%s>\n\t''' % (title, state)
			xml = '''<?xml version="1.0"?>\n<tree string="%s" editable="top" refresh="5" on_write="_on_create_write"%s>\n\t''' % (title, state)
			fields = []

			widths = {
				'ref': 50,
				'statement_id': 50,
				'state': 60,
				'tax_code_id': 50,
				'move_id': 40,
			}
			for field in journal.view_id.columns_id:
				fields.append(field.field)
				attrs = []
				if field.readonly:
					attrs.append('readonly="1"')
				if field.required:
					attrs.append('required="1"')
				else:
					attrs.append('required="0"')
				if field.field == 'partner_id':
					attrs.append('on_change="onchange_partner_id(move_id,partner_id,account_id,debit,credit,((\'journal_id\' in context) and context[\'journal_id\']) or {})"')
				if field.field in widths:
					attrs.append('width="'+str(widths[field.field])+'"')
				xml += '''<field name="%s" %s/>\n''' % (field.field,' '.join(attrs))

			xml += '''</tree>'''
			result['arch'] = xml
			result['fields'] = self.fields_get(cr, uid, fields, context)
		return result

	def unlink(self, cr, uid, ids, context={}, check=True):
		self._update_check(cr, uid, ids, context)
		for line in self.browse(cr, uid, ids, context):
			context['journal_id']=line.journal_id.id
			context['period_id']=line.period_id.id
			result = super(account_move_line, self).unlink(cr, uid, [line.id], context=context)
			if check:
				self.pool.get('account.move').validate(cr, uid, [line.move_id.id], context=context)
		return result

	#
	# TO VERIFY: check if try to write journal of only one line ???
	#
	def write(self, cr, uid, ids, vals, context={}, check=True, update_check=True):
		if update_check:
			self._update_check(cr, uid, ids, context)
		result = super(osv.osv, self).write(cr, uid, ids, vals, context)
		if check:
			done = []
			for line in self.browse(cr, uid, ids):
				if line.move_id.id not in done:
					done.append(line.move_id.id)
					self.pool.get('account.move').validate(cr, uid, [line.move_id.id], context)
		return result

	def _update_journal_check(self, cr, uid, journal_id, period_id, context={}):
		cr.execute('select state from account_journal_period where journal_id=%d and period_id=%d', (journal_id, period_id))
		result = cr.fetchall()
		for (state,) in result:
			if state=='done':
				raise osv.except_osv('Error !', 'You can not add/modify entries in a closed journal.')
		if not result:
			journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context)
			period = self.pool.get('account.period').browse(cr, uid, period_id, context)
			self.pool.get('account.journal.period').create(cr, uid, {
				'name': (journal.code or journal.name)+':'+(period.name or ''),
				'journal_id': journal.id,
				'period_id': period.id
			})
		return True

	def _update_check(self, cr, uid, ids, context={}):
		done = {}
		for line in self.browse(cr, uid, ids, context):
			if line.move_id.state<>'draft':
				raise osv.except_osv('Error !', 'You can not modify or delete a confirmed entry !')
			if line.reconcile_id:
				raise osv.except_osv('Error !', 'You can not modify or delete a reconciled entry !')
			t = (line.journal_id.id, line.period_id.id)
			if t not in done:
				self._update_journal_check(cr, uid, line.journal_id.id, line.period_id.id, context)
				done[t] = True
		return True

	def create(self, cr, uid, vals, context={}, check=True):
		if 'journal_id' in vals and 'journal_id' not in context:
			context['journal_id'] = vals['journal_id']
		if 'period_id' in vals and 'period_id' not in context:
			context['period_id'] = vals['period_id']
		if 'journal_id' not in context and 'move_id' in vals:
			m = self.pool.get('account.move').browse(cr, uid, vals['move_id'])
			context['journal_id'] = m.journal_id.id
			context['period_id'] = m.period_id.id
		self._update_journal_check(cr, uid, context['journal_id'], context['period_id'], context)
		move_id = vals.get('move_id', False)
		journal = self.pool.get('account.journal').browse(cr, uid, context['journal_id'])
		if not move_id:
			if journal.centralisation:
				# use the first move ever created for this journal and period
				cr.execute('select id from account_move where journal_id=%d and period_id=%d order by id limit 1', (context['journal_id'],context['period_id']))
				res = cr.fetchone()
				if res:
					vals['move_id'] = res[0]

			if not vals.get('move_id', False):
				if journal.sequence_id:
					name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id)
					v = {
						'name': name,
						'period_id': context['period_id'],
						'journal_id': context['journal_id']
					}
					move_id = self.pool.get('account.move').create(cr, uid, v, context)
					vals['move_id'] = move_id
				else:
					raise osv.except_osv('No piece number !', 'Can not create an automatic sequence for this piece !\n\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.')

		if ('account_id' in vals) and journal.type_control_ids:
			type = self.pool.get('account.account').browse(cr, uid, vals['account_id']).type
			ok = False
			for t in journal.type_control_ids:
				if type==t.code:
					ok = True
					break
			if not ok:
				raise osv.except_osv('Bad account !', 'You can not use this general account in this journal !')

		result = super(osv.osv, self).create(cr, uid, vals, context)
		if check:
			self.pool.get('account.move').validate(cr, uid, [vals['move_id']], context)
		return result
account_move_line()

class account_tax(osv.osv):
	"""
	A tax object.

	Type: percent, fixed, none, code
		PERCENT: tax = price * amount
		FIXED: tax = price + amount
		NONE: no tax line
		CODE: execute python code. localcontext = {'price_unit':pu, 'address':address_object}
			return result in the context
			Ex: result=round(price_unit*0.21,4)
	"""
	_name = 'account.tax'
	_description = 'Tax'
	_columns = {
		'name': fields.char('Tax Name', size=64, required=True),
		'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the taxes lines from the lowest sequences to the higher ones. The order is important if you have a tax that have several tax childs. In this case, the evaluation order is important."),
		'amount': fields.float('Amount', required=True, digits=(14,4)),
		'active': fields.boolean('Active'),
		'type': fields.selection( [('percent','Percent'), ('fixed','Fixed'), ('none','None'), ('code','Python Code')], 'Tax Type', required=True),
		'applicable_type': fields.selection( [('true','True'), ('code','Python Code')], 'Applicable Type', required=True),
		'domain':fields.char('Domain', size=32, help="This field is only used if you develop your own module allowing developpers to create specific taxes in a custom domain."),
		'account_collected_id':fields.many2one('account.account', 'Collected Tax Account'),
		'account_paid_id':fields.many2one('account.account', 'Paid Tax Account'),
		'parent_id':fields.many2one('account.tax', 'Parent Tax Account', select=True),
		'child_ids':fields.one2many('account.tax', 'parent_id', 'Childs Tax Account'),
		'child_depend':fields.boolean('Tax on Childs', help="Indicate if the tax computation is based on the value computed for the computation of child taxes or based on the total amount."),
		'python_compute':fields.text('Python Code'),
		'python_applicable':fields.text('Python Code'),
		'company_id': fields.many2one('res.company', 'Company'),
		'tax_group': fields.selection([('vat','VAT'),('other','Other')], 'Tax Group', help="If a default tax if given in the partner it only override taxes from account (or product) of the same group."),

		#
		# Fields used for the VAT declaration
		#
		'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="Use this code for the VAT declaration."),
		'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="Use this code for the VAT declaration."),
		'base_sign': fields.float('Base Code Sign', help="Usualy 1 or -1."),
		'tax_sign': fields.float('Tax Code Sign', help="Usualy 1 or -1."),

		# Same fields for refund invoices

		'ref_base_code_id': fields.many2one('account.tax.code', 'Base Code', help="Use this code for the VAT declaration."),
		'ref_tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="Use this code for the VAT declaration."),
		'ref_base_sign': fields.float('Base Code Sign', help="Usualy 1 or -1."),
		'ref_tax_sign': fields.float('Tax Code Sign', help="Usualy 1 or -1."),
	}
	_defaults = {
		'python_compute': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n\nresult = price_unit * 0.10''',
		'applicable_type': lambda *a: 'true',
		'type': lambda *a: 'percent',
		'amount': lambda *a: 0.196,
		'active': lambda *a: 1,
		'sequence': lambda *a: 1,
		'tax_group': lambda *a: 'vat',
		'ref_tax_sign': lambda *a: -1,
		'ref_base_sign': lambda *a: -1,
		'tax_sign': lambda *a: 1,
		'base_sign': lambda *a: 1,
	}
	_order = 'sequence'
	
	def _applicable(self, cr, uid, taxes, price_unit, address_id=None):
		res = []
		for tax in taxes:
			if tax.applicable_type=='code':
				localdict = {'price_unit':price_unit, 'address':self.pool.get('res.partner.address').browse(cr, uid, address_id)}
				exec tax.python_applicable in localdict
				if localdict.get('result', False):
					res.append(tax)
			else:
				res.append(tax)
		return res

	def _unit_compute(self, cr, uid, ids, price_unit, address_id=None):
		taxes = self.browse(cr, uid, ids)
		return self._unit_compute_br(cr, uid, taxes, price_unit, address_id)

	def _unit_compute_br(self, cr, uid, taxes, price_unit, address_id=None):
		taxes = self._applicable(cr, uid, taxes, price_unit, address_id)

		res = []
		for tax in taxes:
			# we compute the amount for the current tax object and append it to the result
			if tax.type=='percent':
				amount = price_unit * tax.amount
				res.append({'id':tax.id, 'name':tax.name, 'amount':amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id})
			elif tax.type=='fixed':
				res.append({'id':tax.id, 'name':tax.name, 'amount':tax.amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id})
			elif tax.type=='code':
				address = address_id and self.pool.get('res.partner.address').browse(cr, uid, address_id) or None
				localdict = {'price_unit':price_unit, 'address':address}
				exec tax.python_compute in localdict
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
				parent_tax = self._unit_compute_br(cr, uid, [t], amount, address_id)
				res.extend(parent_tax)
		return res

	def compute(self, cr, uid, ids, price_unit, quantity, address_id=None):
		"""
		Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.

		RETURN:
			[ tax ]
			tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
			one tax for each tax id in IDS and their childs
		"""
		res = self._unit_compute(cr, uid, ids, price_unit, address_id)
		for r in res:
			r['amount'] = round(quantity * r['amount'],2)
		return res
account_tax()

# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------

class account_budget_post(osv.osv):
	_name = 'account.budget.post'
	_description = 'Budget item'
	_columns = {
		'code': fields.char('Code', size=64, required=True),
		'name': fields.char('Name', size=256, required=True),
		'sens': fields.selection( [('charge','Charge'), ('produit','Product')], 'Direction', required=True),
		'dotation_ids': fields.one2many('account.budget.post.dotation', 'post_id', 'Expenses'),
		'account_ids': fields.many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', 'Accounts'),
	}
	_defaults = {
		'sens': lambda *a: 'produit',
	}

	def spread(self, cr, uid, ids, fiscalyear_id=False, quantity=0.0, amount=0.0):
		dobj = self.pool.get('account.budget.post.dotation')
		for o in self.browse(cr, uid, ids):
			# delete dotations for this post
			dobj.unlink(cr, uid, dobj.search(cr, uid, [('post_id','=',o.id)]))

			# create one dotation per period in the fiscal year, and spread the total amount/quantity over those dotations
			fy = self.pool.get('account.fiscalyear').browse(cr, uid, [fiscalyear_id])[0]
			num = len(fy.period_ids)
			for p in fy.period_ids:
				dobj.create(cr, uid, {'post_id': o.id, 'period_id': p.id, 'quantity': quantity/num, 'amount': amount/num})
		return True
account_budget_post()

class account_budget_post_dotation(osv.osv):
	_name = 'account.budget.post.dotation'
	_description = "Budget item endowment"
	_columns = {
		'name': fields.char('Name', size=64),
		'post_id': fields.many2one('account.budget.post', 'Item', select=True),
		'period_id': fields.many2one('account.period', 'Period'),
		'quantity': fields.float('Quantity', digits=(16,2)),
		'amount': fields.float('Amount', digits=(16,2)),
	}
account_budget_post_dotation()


# ---------------------------------------------------------
# Account Entries Models
# ---------------------------------------------------------

class account_model(osv.osv):
	_name = "account.model"
	_description = "Account Model"
	_columns = {
		'name': fields.char('Model Name', size=64, required=True, help="This is a model for recurring accounting entries"),
		'ref': fields.char('Ref', size=64),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True),
		'lines_id': fields.one2many('account.model.line', 'model_id', 'Model Entries'),
	}
	def generate(self, cr, uid, ids, datas={}, context={}):
		move_ids = []
		for model in self.browse(cr, uid, ids, context):
			period_id = self.pool.get('account.period').find(cr,uid, context=context)
			if not period_id:
				raise osv.except_osv('No period found !', 'Unable to find a valid period !')
			period_id = period_id[0]
			name = model.name
			if model.journal_id.sequence_id:
				name = self.pool.get('ir.sequence').get_id(cr, uid, model.journal_id.sequence_id.id)
			move_id = self.pool.get('account.move').create(cr, uid, {
				'name': name,
				'ref': model.ref,
				'period_id': period_id,
				'journal_id': model.journal_id.id,
			})
			move_ids.append(move_id)
			for line in model.lines_id:
				val = {
					'move_id': move_id,
					'journal_id': model.journal_id.id,
					'period_id': period_id
				}
				val.update({
					'name': line.name,
					'quantity': line.quantity,
					'debit': line.debit,
					'credit': line.credit,
					'account_id': line.account_id.id,
					'move_id': move_id,
					'ref': line.ref,
					'partner_id': line.partner_id.id,
					'date': time.strftime('%Y-%m-%d'),
					'date_maturity': time.strftime('%Y-%m-%d')
				})
				c = context.copy()
				c.update({'journal_id': model.journal_id.id,'period_id': period_id})
				self.pool.get('account.move.line').create(cr, uid, val, context=c)
		return move_ids
account_model()

class account_model_line(osv.osv):
	_name = "account.model.line"
	_description = "Account Model Entries"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the resources from the lowest sequences to the higher ones"),
		'quantity': fields.float('Quantity', digits=(16,2), help="The optionnal quantity on entries"),
		'debit': fields.float('Debit', digits=(16,2)),
		'credit': fields.float('Credit', digits=(16,2)),

		'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade"),

		'model_id': fields.many2one('account.model', 'Model', required=True, ondelete="cascade", select=True),

		'ref': fields.char('Ref.', size=16),

		'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optionnal other currency."),
		'currency_id': fields.many2one('res.currency', 'Currency'),

		'partner_id': fields.many2one('res.partner', 'Partner Ref.'),
		'date_maturity': fields.selection([('today','Date of the day'), ('partner','Partner Payment Term')], 'Maturity date', help="The maturity date of the generated entries for this model. You can chosse between the date of the creation action or the the date of the creation of the entries plus the partner payment terms."),
		'date': fields.selection([('today','Date of the day'), ('partner','Partner Payment Term')], 'Current Date', required=True, help="The date of the generated entries"),
	}
	_defaults = {
		'date': lambda *a: 'today'
	}
	_order = 'sequence'
	_sql_constraints = [
		('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in model !'),
		('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in model !'),
	]
account_model_line()

# ---------------------------------------------------------
# Account Subscription
# ---------------------------------------------------------


class account_subscription(osv.osv):
	_name = "account.subscription"
	_description = "Account Subscription"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'ref': fields.char('Ref.', size=16),
		'model_id': fields.many2one('account.model', 'Model', required=True),

		'date_start': fields.date('Starting date', required=True),
		'period_total': fields.integer('Number of period', required=True),
		'period_nbr': fields.integer('Period', required=True),
		'period_type': fields.selection([('day','days'),('month','month'),('year','year')], 'Period Type', required=True),
		'state': fields.selection([('draft','Draft'),('running','Running'),('done','Done')], 'State', required=True, readonly=True),

		'lines_id': fields.one2many('account.subscription.line', 'subscription_id', 'Subscription Lines')
	}
	_defaults = {
		'date_start': lambda *a: time.strftime('%Y-%m-%d'),
		'period_type': lambda *a: 'month',
		'period_total': lambda *a: 12,
		'period_nbr': lambda *a: 1,
		'state': lambda *a: 'draft',
	}
	def state_draft(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'draft'})
		return False

	def check(self, cr, uid, ids, context={}):
		todone = []
		for sub in self.browse(cr, uid, ids, context):
			ok = True
			for line in sub.lines_id:
				if not line.move_id.id:
					ok = False
					break
			if ok:
				todone.append(sub.id)
		if len(todone):
			self.write(cr, uid, todone, {'state':'done'})
		return False

	def remove_line(self, cr, uid, ids, context={}):
		toremove = []
		for sub in self.browse(cr, uid, ids, context):
			for line in sub.lines_id:
				if not line.move_id.id:
					toremove.append(line.id)
		if len(toremove):
			self.pool.get('account.subscription.line').unlink(cr, uid, toremove)
		self.write(cr, uid, ids, {'state':'draft'})
		return False

	def compute(self, cr, uid, ids, context={}):
		for sub in self.browse(cr, uid, ids, context):
			ds = sub.date_start
			for i in range(sub.period_total):
				self.pool.get('account.subscription.line').create(cr, uid, {
					'date': ds,
					'subscription_id': sub.id,
				})
				if sub.period_type=='day':
					ds = (mx.DateTime.strptime(ds, '%Y-%m-%d') + RelativeDateTime(days=sub.period_nbr)).strftime('%Y-%m-%d')
				if sub.period_type=='month':
					ds = (mx.DateTime.strptime(ds, '%Y-%m-%d') + RelativeDateTime(months=sub.period_nbr)).strftime('%Y-%m-%d')
				if sub.period_type=='year':
					ds = (mx.DateTime.strptime(ds, '%Y-%m-%d') + RelativeDateTime(years=sub.period_nbr)).strftime('%Y-%m-%d')
		self.write(cr, uid, ids, {'state':'running'})
		return True
account_subscription()

class account_subscription_line(osv.osv):
	_name = "account.subscription.line"
	_description = "Account Subscription Line"
	_columns = {
		'subscription_id': fields.many2one('account.subscription', 'Subscription', required=True, select=True),
		'date': fields.date('Date', required=True),
		'move_id': fields.many2one('account.move', 'Entry'),
	}
	_defaults = {
	}
	def move_create(self, cr, uid, ids, context={}):
		tocheck = {}
		for line in self.browse(cr, uid, ids, context):
			datas = {
				'date': line.date,
			}
			ids = self.pool.get('account.model').generate(cr, uid, [line.subscription_id.model_id.id], datas, context)
			tocheck[line.subscription_id.id] = True
			self.write(cr, uid, [line.id], {'move_id':ids[0]})
		if tocheck:
			self.pool.get('account.subscription').check(cr, uid, tocheck.keys(), context)
		return True
	_rec_name = 'date'
account_subscription_line()


