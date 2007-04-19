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

		if move.journal_id.type in ('purchase', 'sale'):
			field_base=''
			if move.journal_id.type=='purchase':
				field_base='ref_'
			for t in taxes:
				if not taxes[t] and t[0]:
					s=0
					for l in move.line_id:
						key = (l.debit and 'account_paid_id') or 'account_collected_id'
						for tax in self.pool.get('account.tax').compute(cr, uid, l.account_id.tax_ids, l.debit or l.credit, 1, False):
							if (tax[key] == t[0]) and (tax[field_base+'tax_code_id']==t[1]):
								if l.debit:
									s += tax['amount']
								else:
									s -= tax['amount']
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

	def _check_no_view(self, cr, uid, ids):
		lines = self.browse(cr, uid, ids)
		for l in lines:
			if l.account_id.type == 'view':
				return False
		return True

	_constraints = [
		(_check_no_view, 'You can not create move line on view account.', ['account_id'])
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
			raise Exception('Entries are not of the same account or already reconciled ! ')
		if r[0][1] != None:
			raise Exception('Some entries are already reconciled !')
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
				if field.field=='account_id' and journal.id:
					attrs.append('domain="[(\'journal_id\', \'=\', '+str(journal.id)+'),(\'type\',\'&lt;&gt;\',\'view\')]"')
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


class account_bank_statement_reconcile(osv.osv):
	_inherit = "account.bank.statement.reconcile"
	_columns = {
		'line_ids': fields.many2many('account.move.line', 'account_bank_statement_line_rel', 'statement_id', 'line_id', 'Entries'),
	}
account_bank_statement_reconcile()


