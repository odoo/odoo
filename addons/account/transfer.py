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
import ir

class account_transfer(osv.osv):
	_name = "account.transfer"
	_description = "Money Transfer"
	def _get_period(self, cr, uid, context):
		periods = self.pool.get('account.period').find(cr, uid)
		if periods:
			return periods[0]
		else:
			return False
	_columns = {
		'name': fields.char('Description', size=64, required=True),
		'state': fields.selection( (('draft','draft'),('posted','posted')),'State', readonly=True),
		'partner_id': fields.many2one('res.partner', 'Partner', states={'posted':[('readonly',True)]}),
		'project_id': fields.many2one('account.analytic.account', 'Analytic Account', states={'posted':[('readonly',True)]}),

		'journal_id': fields.many2one('account.journal', 'Journal', required=True, states={'posted':[('readonly',True)]}),
		'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),

		'date': fields.date('Payment Date', required=True, states={'posted':[('readonly',True)]}),
		'type': fields.selection([
			('undefined','Undefined'),
			('in_payment','Incoming Customer Payment'),
			('out_payment','Outgoing Supplier Payment'),
			('expense', 'Direct Expense'),
			('transfer','Money Transfer'),
			('change','Currency Change'),
			('refund','Customer Refund'),
			('sale','Manual Sale'),
#			('expense reimburse','Remboursement Depense')
		], 'Transfer Type', required=True, states={'posted':[('readonly',True)]} ),
		'reference': fields.char('Reference',size=64),
		'account_src_id': fields.many2one('account.account', 'Source Account', required=True, states={'posted':[('readonly',True)]}),
		'account_dest_id': fields.many2one('account.account', 'Destination Account', required=True, states={'posted':[('readonly',True)]}),
		'amount': fields.float('Amount', digits=(16,2), required=True, states={'posted':[('readonly',True)]}),
		'change': fields.float('Amount Changed', digits=(16,2), states={'posted':[('readonly',True)]}, readonly=True),
		'move_id': fields.many2one('account.move', 'Entry', readonly=True),
		'adjust_amount': fields.float('Adjustement amount', states={'posted':[('readonly',True)]}),
		'adjust_account_id': fields.many2one('account.account', 'Adjustement Account', states={'posted':[('readonly',True)]}),
		'invoice_id': fields.many2many('account.invoice','account_transfer_invoice','transfer_id','invoice_id','Invoices', states={'posted':[('readonly',True)]}, help="You can select customer or supplier invoice that are related to this payment. This is optionnal but if you specify the invoices, Tiny ERP will automatically reconcile the entries and mark invoices as paid."),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'state': lambda *a: 'draft',
		'period_id' : _get_period,
	}

	def unlink(self, cr, uid, ids):
		transfers = self.read(cr, uid, ids, ['state'])
		unlink_ids = []
		for t in transfers:
			if t['state']=='draft':
				unlink_ids.append(t['id'])
			else:
				raise osv.except_osv('Invalid action !', 'Cannot delete transfer(s) which are already posted !')
		osv.osv.unlink(self, cr, uid, unlink_ids)
		return True

	def _onchange_type_domain(self,cr,uid,ids,type):
		type_acc={
			'in_payment': ('receivable','cash'),
			'out_payment': ('cash','payable'),
			'expense':  ('cash','expense'),
			'transfer': ('cash','cash'),
			'change':   ('cash','cash'),
			'refund':   ('receivable','income'),
			'sale':     ('income','cash'),
		}
		d = {'account_src_id': [('type','<>','view'), ('type', '<>', 'closed')], 'account_dest_id': [('type','<>','view'), ('type', '<>', 'closed')]}
		if type_acc.has_key(type):
			d['account_src_id'].append(('type','=',type_acc[type][0]))
			d['account_dest_id'].append(('type','=',type_acc[type][1]))
		return d

	def onchange_type(self, cr, uid, ids, type):
		ro = {'change':type!='change',
			'adjust_amount': type not in ('in_payment','out_payment'),
			'adjust_account_id': type not in ('in_payment','out_payment')}
		d=self._onchange_type_domain(cr,uid,ids,type)
		return {'domain': d, 'value': {'account_src_id': False, 'account_dest_id': False}, 'readonly':ro}

	def _onchange_account_domain(self,cr,uid,ids,type, account_src, account_dest):
		d=self._onchange_type_domain(cr,uid,ids,type)
		if type != 'change':
			if account_src and not account_dest:
				cr.execute("SELECT currency_id FROM account_account WHERE id=%d",(account_src,))
				d['account_dest_id'].append(('currency_id','=',cr.fetchall()[0][0]))
			if account_dest and not account_src:
				cr.execute("SELECT currency_id FROM account_account WHERE id=%d",(account_dest,))
				d['account_src_id'].append(('currency_id','=',cr.fetchall()[0][0]))
		return d

	def onchange_account(self, cr, uid, ids, type, account_src, account_dest):
		d=self._onchange_account_domain(cr,uid,ids,type,account_src,account_dest)
		return {'domain': d}

	def onchange_partner(self, cr, uid, ids, type, partner_id):
		if partner_id:
			value={}
			
			if type=='in_payment':
				a = self.pool.get('res.partner').browse(cr, uid, partner_id).property_account_receivable[0]
				value['account_src_id'] = a
				value['account_dest_id'] = False
				
				# compute the amount this partner owe us (the sum of all move lines which have not been matched)
				cr.execute("SELECT COALESCE(SUM(debit-credit),0) from account_move_line where account_id=%d and partner_id=%d and reconcile_id is null and state<>'draft'", (a, partner_id))
				value['amount'] = cr.fetchone()[0]
				
				d = self._onchange_account_domain(cr,uid,ids,type, value['account_src_id'], value['account_dest_id'])
				return {'domain': d, 'value': value}
				
			elif type=='out_payment':
				a = self.pool.get('res.partner').browse(cr, uid, partner_id).property_account_payable[0]
				value['account_src_id'] = False
				value['account_dest_id'] = a
				
				# compute the amount we owe this partner (the sum of all move lines which have not been matched)
				cr.execute("SELECT COALESCE(SUM(debit-credit),0) from account_move_line where account_id=%d and partner_id=%d and reconcile_id is null and state<>'draft'", (a,partner_id))
				value['amount'] = -cr.fetchone()[0]

				# get the new domain
				d = self._onchange_account_domain(cr,uid,ids,type, value['account_src_id'], value['account_dest_id'])
				return {'domain': d, 'value': value}
				
		return self.onchange_type(cr,uid,ids, type)

	def pay_validate(self, cr, uid, ids, *args):
		transfers = self.read(cr, uid, ids)
		for pay in transfers:
			if pay['state']!='draft':
				continue
			name = pay['name']

			partner_id = (pay['partner_id'] or None) and pay['partner_id'][0]
			project_id = (pay['project_id'] or None) and pay['project_id'][0]

			# create two move lines (one for the source account and one for the destination account)
			l = {
				'name':name,
				'journal_id': pay['journal_id'][0],
				'period_id': pay['period_id'][0],
			}
#CHECKME: why don't these two lines have period_id and journal_id defined?
			l2 = {
				'name':name,
				'credit':pay['amount']<0 and -pay['amount'],
				'debit':pay['amount']>0 and pay['amount'],
				'account_id': pay['account_dest_id'][0],
				'partner_id': partner_id
			}
			l1 = {
				'name':name,
				'debit':pay['amount']<0 and -pay['amount'],
				'credit':pay['amount']>0 and pay['amount'],
				'account_id': pay['account_src_id'][0],
				'partner_id': partner_id
			}
			line_id = [l1, l2]

			# possibly create two more lines if there is an adjustment
			if False and pay['adjust_amount']:
				if pay['adjust_account_id']:
					la = l.copy()
					la.update({'name': name+' adjustment', 'credit':pay['adjust_amount']<0 and -pay['adjust_amount'], 'debit':pay['adjust_amount']>0 and pay['adjust_amount'], 'account_id': pay['adjust_account_id'][0],})
					line_id.append(la)
					la = l.copy()
					la.update({'name': name+' adjustment', 'debit':pay['adjust_amount']<0 and -pay['adjust_amount'], 'credit':pay['adjust_amount']>0 and pay['adjust_amount'], 'account_id': pay['account_src_id'][0],})
					line_id.append(la)
				else:
					raise Exception('No Adjust Account !', 'missing adjust account')
					
			# create the new move and its 2 (or 4) lines
			move = l.copy()
			move['line_id'] = [(0, 0, l) for l in line_id]
			move_id = self.pool.get('account.move').create(cr, uid, move)
			
			# get account_id depending on the type of transfer
			tmp = {'in_payment':pay['account_src_id'][0], 'out_payment':pay['account_dest_id'][0]}
			account_id = tmp.get(pay['type'], None)
			
			if account_id and len(pay['invoice_id']):
				# get the ids of all moves lines which 1) use account_id 2) are not matched 3) correspond to the selected invoices
				inv_set = ",".join(map(str, pay["invoice_id"]))
				query = "SELECT id FROM account_move_line "+\
				        "WHERE account_id=%d "+\
				        "AND reconcile_id IS NULL "+\
				        "AND move_id IN (SELECT move_id FROM account_invoice WHERE id IN ("+inv_set+"))"
				cr.execute(query, (account_id,))
				l_ids = [i[0] for i in cr.fetchall()]
				if not l_ids:
					print 'Error: no unmatched move line found for account %d and invoices %s while confirming transfer %d' % (account_id, pay['invoice_id'], pay['id'])
					continue
				
				# compute the sum of those lines
				l_set = ",".join(map(str, l_ids))
				cr.execute("SELECT SUM(debit-credit) FROM account_move_line WHERE id IN (" + l_set + ")")
				s = cr.fetchone()[0]
				
				# if that amount = the amount paid, match those lines (from the selected invoices) with the current transfer
				types = {'out_payment': -1, 'in_payment': 1}
				sign = types.get(pay['type'], 1)
				if (s-(pay['adjust_amount'] or 0.0))==sign*pay['amount']:
					# get the id of the move_line for the current transfer
					cr.execute("SELECT id FROM account_move_line WHERE account_id=%d AND move_id=%d", (account_id,move_id))
					l_ids.append(cr.fetchall()[0][0])
					self.pool.get('account.move.line').reconcile(cr, uid, l_ids, writeoff_period_id=pay['period_id'][0], writeoff_journal_id=pay['journal_id'][0], writeoff_acc_id=pay['adjust_account_id'] and pay['adjust_account_id'][0])
				else:
					raise osv.except_osv('Warning !', 'Could not confirm payment because its amount (%.2f) is different from the selected invoice(s) amount (%.2f) !' % (pay['amount']+pay['adjust_amount'],s))
					
			elif account_id and partner_id:
				# compute the sum of all move lines for this account and partner which were not matched
				cr.execute("SELECT SUM(debit-credit) FROM account_move_line WHERE account_id=%d AND partner_id=%d AND reconcile_id is null", (account_id, partner_id))
				s = cr.fetchone()[0]
				
				# if that amount is 0, we match those move lines together
				if s==0.0:
					cr.execute("select id from account_move_line where account_id=%d and partner_id=%d and reconcile_id is null", (account_id, partner_id))
					ids2 = [id for (id,) in cr.fetchall()]
					if len(ids2):
						self.pool.get('account.move.line').reconcile(cr, uid, ids2, writeoff_period_id=pay['period_id'][0], writeoff_journal_id=pay['journal_id'][0], writeoff_acc_id=pay['adjust_account_id'] and pay['adjust_account_id'][0])

			# change transfer state and assign it its move
			self.write(cr, uid, [pay['id']], {'state':'posted', 'move_id': move_id})
		return True

	def pay_cancel(self, cr, uid, ids, *args):
		pays = self.read(cr, uid, ids, ['move_id'])
		self.pool.get('account.move').unlink(cr, uid, [ x['move_id'][0] for x in pays if x['move_id']] )
		self.write(cr, uid, ids, {'state':'draft'})
		return True
account_transfer()
