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

#
# use a sequence for names ?
# 
class account_bank_statement(osv.osv):
	def _default_journal_id(self, cr, uid, context={}):
		if context.get('journal_id', False):
			return context['journal_id']
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
					'ref': move.invoice_id and move.invoice_id.number or '' 
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
		'invoice_id': fields.many2one('account.invoice', 'Invoice', states={'confirm':[('readonly',True)]}),


	}
	_defaults = {
		'name': lambda self,cr,uid,context={}: self.pool.get('ir.sequence').get(cr, uid, 'account.bank.statement.line'),
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'type': lambda *a: 'general',
	}
account_bank_statement_line()




