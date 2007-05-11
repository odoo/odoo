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
		'line_ids': fields.one2many('account.payment.term.line', 'payment_id', 'Terms'),
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
		'value': fields.selection([('procent','Percent'),('balance','Balance'),('fixed','Fixed Amount')], 'Value',required=True),
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

	def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}):
		pos = 0
		while pos<len(args):
			if args[pos][0]=='journal_id':
				jour = self.pool.get('account.journal').browse(cr, uid, args[pos][2])
				if (not (jour.account_control_ids or jour.type_control_ids)) or not args[pos][2]:
					del args[pos]
					continue
				ids3 = map(lambda x: x.code, jour.type_control_ids)
				ids1 = super(account_account,self).search(cr, uid, [('type','in',ids3)])
				ids1 += map(lambda x: x.id, jour.account_control_ids)
				args[pos] = ('id','in',ids1)
			pos+=1
		return super(account_account,self).search(cr, uid, args, offset, limit, order, context=context)

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
		cr.execute("SELECT a.id, a.company_id FROM account_account a where id in (%s)" % acc_set)
		resc = dict(cr.fetchall())
		cr.execute("SELECT id, currency_id FROM res_company")
		rescur = dict(cr.fetchall())
		for id in ids:
			ids3 = self.search(cr, uid, [('parent_id', 'child_of', [id])])
			to_currency_id = rescur[resc[id]]
			for idx in ids3:
				if idx <> id:
					res.setdefault(id, 0.0)
					if resc[idx]<>resc[id] and resc[idx] and resc[id]:
						from_currency_id = rescur[resc[idx]]
						res[id] += self.pool.get('res.currency').compute(cr, uid, from_currency_id, to_currency_id, res.get(idx, 0.0), context=context)
					else:
						res[id] += res.get(idx, 0.0)
		for id in ids:
			res[id] = round(res.get(id,0.0), 2)
		return res

	def _get_company_currency(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for rec in self.browse(cr, uid, ids, context):
			result[rec.id] = (rec.company_id.currency_id.id,rec.company_id.currency_id.code)
		return result

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

		'active': fields.boolean('Active'),
		'note': fields.text('Note'),
		'company_currency_id': fields.function(_get_company_currency, method=True, type='many2one', relation='res.currency', string='Currency'),
		'company_id': fields.many2one('res.company', 'Company', required=True),
	}

	def _default_company(self, cr, uid, context={}):
		user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		if user.company_id:
			return user.company_id.id
		return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
	_defaults = {
		'sign': lambda *a: 1,
		'type': lambda *a: 'view',
		'active': lambda *a: True,
		'reconcile': lambda *a: False,
		'close_method': lambda *a: 'balance',
		'company_id': _default_company,
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

	def copy(self, cr, uid, id, default=None, context={}):
		account = self.browse(cr, uid, id, context=context)
		new_child_ids = []
		default['parent_id'] = False
		if account:
			for child in account.child_id:
				new_child_ids.append(self.copy(cr, uid, child.id, default, context=context))
			default['child_id'] = [(6, 0, new_child_ids)]
		else:
			default['child_id'] = False
		return super(account_account, self).copy(cr, uid, id, default, context=context)
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
		'code': fields.char('Code', size=16),
		'type': fields.selection([('sale','Sale'), ('purchase','Purchase'), ('cash','Cash'), ('general','General'), ('situation','Situation')], 'Type', size=32, required=True),

		'type_control_ids': fields.many2many('account.account.type', 'account_journal_type_rel', 'journal_id','type_id', 'Type Controls', domain=[('code','<>','view')]),
		'account_control_ids': fields.many2many('account.account', 'account_account_type_rel', 'journal_id','account_id', 'Account', domain=[('type','<>','view')]),

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
		'iban': fields.char('IBAN', size=34),
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
		'date_start': fields.date('Start date', required=True),
		'date_stop': fields.date('End date', required=True),
		'period_ids': fields.one2many('account.period', 'fiscalyear_id', 'Periods'),
		'state': fields.selection([('draft','Draft'), ('done','Done')], 'State', redonly=True),
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

		if not 'name' in vals:
			journal = self.pool.get('account.journal').browse(cr, uid, context.get('journal_id', vals.get('journal_id', False)))
			if journal.sequence_id:
				vals['name'] = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id)
			else:
				raise osv.except_osv('Error', 'No sequence defined in the journal !')
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
			company_id=None
			for line in move.line_id:
				amount += line.debit - line.credit
				line_ids.append(line.id)
				if line.state=='draft':
					line_draft_ids.append(line.id)

				if not company_id:
					company_id = line.account_id.company_id.id
				if not company_id == line.account_id.company_id.id:
					raise osv.except_osv('Error', 'Couldn\'t create move between different companies')

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
						if code and not (line.tax_code_id or line.tax_amount): 
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
					if (code or amount) and not (line.tax_code_id or line.tax_amount):
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
					#'tax_amount': False,
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
		'line_ids': fields.one2many('account.move.line', 'tax_code_id', 'Lines'),
		'company_id': fields.many2one('res.company', 'Company', required=True),
	}
	def _default_company(self, cr, uid, context={}):
		user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		if user.company_id:
			return user.company_id.id
		return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
	_defaults = {
		'company_id': _default_company,
	}
	_order = 'name'
account_tax_code()

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
		'account_collected_id':fields.many2one('account.account', 'Invoice Tax Account'),
		'account_paid_id':fields.many2one('account.account', 'Refund Tax Account'),
		'parent_id':fields.many2one('account.tax', 'Parent Tax Account', select=True),
		'child_ids':fields.one2many('account.tax', 'parent_id', 'Childs Tax Account'),
		'child_depend':fields.boolean('Tax on Childs', help="Indicate if the tax computation is based on the value computed for the computation of child taxes or based on the total amount."),
		'python_compute':fields.text('Python Code'),
		'python_compute_inv':fields.text('Python Code (reverse)'),
		'python_applicable':fields.text('Python Code'),
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
		'include_base_amount': fields.boolean('Include in base amount', help="Indicate if the amount of tax must be included in the base amount for the computation of the next taxes"),
		'company_id': fields.many2one('res.company', 'Company', required=True),
	}

	def _default_company(self, cr, uid, context={}):
		user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		if user.company_id:
			return user.company_id.id
		return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
	_defaults = {
		'python_compute': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n# product : product.product object or None\n# partner : res.partner object or None\n\nresult = price_unit * 0.10''',
		'python_compute_inv': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n# product : product.product object or False\n\nresult = price_unit * 0.10''',
		'applicable_type': lambda *a: 'true',
		'type': lambda *a: 'percent',
		'amount': lambda *a: 0,
		'active': lambda *a: 1,
		'sequence': lambda *a: 1,
		'tax_group': lambda *a: 'vat',
		'ref_tax_sign': lambda *a: -1,
		'ref_base_sign': lambda *a: -1,
		'tax_sign': lambda *a: 1,
		'base_sign': lambda *a: 1,
		'include_base_amount': lambda *a: False,
		'company_id': _default_company,
	}
	_order = 'sequence'
	
	def _applicable(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None):
		res = []
		for tax in taxes:
			if tax.applicable_type=='code':
				localdict = {'price_unit':price_unit, 'address':self.pool.get('res.partner.address').browse(cr, uid, address_id), 'product':product, 'partner':partner}
				exec tax.python_applicable in localdict
				if localdict.get('result', False):
					res.append(tax)
			else:
				res.append(tax)
		return res

	def _unit_compute(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None):
		taxes = self._applicable(cr, uid, taxes, price_unit, address_id, product, partner)

		res = []
		cur_price_unit=price_unit
		for tax in taxes:
			# we compute the amount for the current tax object and append it to the result
			if tax.type=='percent':
				amount = cur_price_unit * tax.amount
				res.append({'id':tax.id, 'name':tax.name, 'amount':amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id, 'base_code_id': tax.base_code_id.id, 'ref_base_code_id': tax.ref_base_code_id.id, 'sequence': tax.sequence, 'base_sign': tax.base_sign, 'tax_sign': tax.tax_sign, 'ref_base_sign': tax.ref_base_sign, 'ref_tax_sign': tax.ref_tax_sign, 'price_unit': cur_price_unit, 'tax_code_id': tax.tax_code_id.id, 'ref_tax_code_id': tax.ref_tax_code_id.id,})
			elif tax.type=='fixed':
				res.append({'id':tax.id, 'name':tax.name, 'amount':tax.amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id, 'base_code_id': tax.base_code_id.id, 'ref_base_code_id': tax.ref_base_code_id.id, 'sequence': tax.sequence, 'base_sign': tax.base_sign, 'tax_sign': tax.tax_sign, 'ref_base_sign': tax.ref_base_sign, 'ref_tax_sign': tax.ref_tax_sign, 'price_unit': 1, 'tax_code_id': tax.tax_code_id.id, 'ref_tax_code_id': tax.ref_tax_code_id.id,})
			elif tax.type=='code':
				address = address_id and self.pool.get('res.partner.address').browse(cr, uid, address_id) or None
				localdict = {'price_unit':cur_price_unit, 'address':address, 'product':product, 'partner':partner}
				exec tax.python_compute in localdict
				amount = localdict['result']
				res.append({
					'id': tax.id,
					'name': tax.name,
					'amount': amount,
					'account_collected_id': tax.account_collected_id.id,
					'account_paid_id': tax.account_paid_id.id,
					'base_code_id': tax.base_code_id.id,
					'ref_base_code_id': tax.ref_base_code_id.id,
					'sequence': tax.sequence,
					'base_sign': tax.base_sign,
					'tax_sign': tax.tax_sign,
					'ref_base_sign': tax.ref_base_sign,
					'ref_tax_sign': tax.ref_tax_sign,
					'price_unit': cur_price_unit,
					'tax_code_id': tax.tax_code_id.id,
					'ref_tax_code_id': tax.ref_tax_code_id.id,
				})
			amount2 = res[-1]['amount']
			if len(tax.child_ids):
				if tax.child_depend:
					del res[-1]
					amount = amount2
				else:
					amount = amount2
			for t in tax.child_ids:
				parent_tax = self._unit_compute(cr, uid, [t], amount, address_id)
				res.extend(parent_tax)
			if tax.include_base_amount:
				cur_price_unit+=amount2
		return res

	def compute(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):

		"""
		Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.

		RETURN:
			[ tax ]
			tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
			one tax for each tax id in IDS and their childs
		"""
		res = self._unit_compute(cr, uid, taxes, price_unit, address_id, product, partner)
		for r in res:
			r['amount'] *= quantity
		return res

	def _unit_compute_inv(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None):
		taxes = self._applicable(cr, uid, taxes, price_unit, address_id, product, partner)

		res = []
		taxes.reverse()
		cur_price_unit=price_unit
		for tax in taxes:
			# we compute the amount for the current tax object and append it to the result
			if tax.type=='percent':
				amount = cur_price_unit - (cur_price_unit / (1 + tax.amount))
				res.append({'id':tax.id, 'name':tax.name, 'amount':amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id, 'base_code_id': tax.base_code_id.id, 'ref_base_code_id': tax.ref_base_code_id.id, 'sequence': tax.sequence, 'base_sign': tax.base_sign, 'tax_sign': tax.tax_sign, 'ref_base_sign': tax.ref_base_sign, 'ref_tax_sign': tax.ref_tax_sign, 'price_unit': cur_price_unit - amount, 'tax_code_id': tax.tax_code_id.id, 'ref_tax_code_id': tax.ref_tax_code_id.id,})
			elif tax.type=='fixed':
				res.append({'id':tax.id, 'name':tax.name, 'amount':tax.amount, 'account_collected_id':tax.account_collected_id.id, 'account_paid_id':tax.account_paid_id.id, 'base_code_id': tax.base_code_id.id, 'ref_base_code_id': tax.ref_base_code_id.id, 'sequence': tax.sequence, 'base_sign': tax.base_sign, 'tax_sign': tax.tax_sign, 'ref_base_sign': tax.ref_base_sign, 'ref_tax_sign': tax.ref_tax_sign, 'price_unit': 1, 'tax_code_id': tax.tax_code_id.id, 'ref_tax_code_id': tax.ref_tax_code_id.id,})
			elif tax.type=='code':
				address = address_id and self.pool.get('res.partner.address').browse(cr, uid, address_id) or None
				localdict = {'price_unit':cur_price_unit, 'address':address, 'product':product, 'partner':partner}
				exec tax.python_compute_inv in localdict
				amount = localdict['result']
				res.append({
					'id': tax.id,
					'name': tax.name,
					'amount': amount,
					'account_collected_id': tax.account_collected_id.id,
					'account_paid_id': tax.account_paid_id.id,
					'base_code_id': tax.base_code_id.id,
					'ref_base_code_id': tax.ref_base_code_id.id,
					'sequence': tax.sequence,
					'base_sign': tax.base_sign,
					'tax_sign': tax.tax_sign,
					'ref_base_sign': tax.ref_base_sign,
					'ref_tax_sign': tax.ref_tax_sign,
					'price_unit': cur_price_unit - amount,
					'tax_code_id': tax.tax_code_id.id,
					'ref_tax_code_id': tax.ref_tax_code_id.id,
				})
			amount2 = res[-1]['amount']
			if len(tax.child_ids):
				if tax.child_depend:
					del res[-1]
					amount = amount2
				else:
					amount = amount2
			for t in tax.child_ids:
				parent_tax = self._unit_compute_inv(cr, uid, [t], amount, address_id)
				res.extend(parent_tax)
			if tax.include_base_amount:
				cur_price_unit-=amount
		taxes.reverse()
		return res

	def compute_inv(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):
		"""
		Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.
		Price Unit is a VAT included price

		RETURN:
			[ tax ]
			tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
			one tax for each tax id in IDS and their childs
		"""
		res = self._unit_compute_inv(cr, uid, taxes, price_unit, address_id, product, partner=None)
		for r in res:
			r['amount'] *= quantity
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


