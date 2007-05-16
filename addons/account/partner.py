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

from osv import fields, osv
import ir

class res_partner(osv.osv):
	_name = 'res.partner'
	_inherit = 'res.partner'
	_description = 'Partner'
	def _credit_get(self, cr, uid, ids, name, arg, context):
		res={}
		try:
			for partner in self.browse(cr, uid, ids, context):
				id = partner.id
				acc = partner.property_account_receivable[0]
				cr.execute("select sum(debit-credit) from account_move_line where account_id=%d and partner_id=%d and reconcile_id is null and state<>'draft'", (acc, id))
				res[id]=cr.fetchone()[0] or 0.0
		except:
			for id in ids:
				res[id]=0.0
		return res

	def _debit_get(self, cr, uid, ids, name, arg, context):
		res={}
		try:
			for partner in self.browse(cr, uid, ids, context):
				id = partner.id
				acc = partner.property_account_payable[0]
				cr.execute("select sum(debit-credit) from account_move_line where account_id=%d and partner_id=%d and reconcile_id is null and state<>'draft'", (acc, id))
				res[id]=cr.fetchone()[0] or 0.0
		except:
			for id in ids:
				res[id]=0.0
		return res

	def _credit_search(self, cr, uid, obj, name, args):
		if not len(args):
			return []
		where = ' and '.join(map(lambda x: '(sum(debit-credit)'+x[1]+str(x[2])+')',args))
		cr.execute('select partner_id from account_move_line where account_id in (select id from account_account where type=%s) and reconcile_id is null and state<>\'draft\' and partner_id is not null group by partner_id having '+where, ('receivable',) )
		res = cr.fetchall()
		if not len(res):
			return [('id','=','0')]
		return [('id','in',map(lambda x:x[0], res))]

	def _debit_search(self, cr, uid, obj, name, args):
		if not len(args):
			return []
		where = ' and '.join(map(lambda x: '(sum(debit-credit)'+x[1]+str(x[2])+')',args))
		cr.execute('select partner_id from account_move_line where account_id in (select id from account_account where type=%s) and reconcile_id is null and state<>\'draft\'and partner_id is not null group by partner_id having '+where, ('payable',) )
		res = cr.fetchall()
		if not len(res):
			return [('id','=','0')]
		return [('id','in',map(lambda x:x[0], res))]

	_columns = {
		'credit': fields.function(_credit_get, fnct_search=_credit_search, method=True, string='Receivable'),
		'debit': fields.function(_debit_get, fnct_search=_debit_search, method=True, string='Payable'),
		'debit_limit': fields.float('Debit Limit'),
		'credit_limit': fields.float('Credit Limit'),
		'property_account_payable': fields.property(
		  'account.account',
		  type='many2one', 
		  relation='account.account', 
		  string="Account Payable", 
		  method=True,
		  view_load=True,
		  group_name="Accounting Properties",
		  help="This account will be used, instead of the default one, as the payable account for the current partner"),
		'property_account_receivable': fields.property(
		'account.account',
		  type='many2one', 
		  relation='account.account', 
		  string="Account Receivable", 
		  method=True,
		  view_load=True,
		  group_name="Accounting Properties",
		  help="This account will be used, instead of the default one, as the receivable account for the current partner"),
		'property_account_tax': fields.property(
		  'account.tax',
		  type='many2one', 
		  relation='account.tax', 
		  string="Default Tax", 
		  method=True,
		  view_load=True,
		  group_name="Accounting Properties",
		  help="This tax will be used, instead of the default one."),
		'property_payment_term': fields.property(
		  'account.payment.term',
		  type='many2one', 
		  relation='account.payment.term', 
		  string ='Payment Term',
		  method=True,
		  view_load=True,
		  group_name="Accounting Properties",
		  help="This payment term will be used, instead of the default one, for the current partner"),
	}
res_partner()


