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


class account_report(osv.osv):
	_name = "account.report.report"
	_description = "Account reporting"
	_color = [
			('', ''),
			('green','Green'),
			('red','Red'),
			('pink','Pink'),
			('blue','Blue'),
			('yellow','Yellow'),
			('cyan','Cyan'),
			('lightblue','Light Blue'),
			('orange','Orange'),
			]
	_style = [
			('1','Header 1'),
			('2','Header 2'),
			('3','Header 3'),
			('4','Header 4'),
			('5','Normal'),
			('6', 'Small'),
			]

	def _amount_get(self, cr, uid, ids, field_name, arg, context={}):
		def _calc_credit(*code):
			acc = self.pool.get('account.account')
			acc_id = acc.search(cr, uid, [('code','in',code)])
			return reduce(lambda y,x=0: x.credit+y, acc.browse(cr, uid, acc_id, context),0)
		def _calc_debit(*code):
			acc = self.pool.get('account.account')
			acc_id = acc.search(cr, uid, [('code','in',code)])
			return reduce(lambda y,x=0: x.debit+y, acc.browse(cr, uid, acc_id, context),0)
		def _calc_balance(*code):
			acc = self.pool.get('account.account')
			acc_id = acc.search(cr, uid, [('code','in',code)])
			return reduce(lambda y,x=0: x.balance+y, acc.browse(cr, uid, acc_id, context),0)
		def _calc_report(*code):
			acc = self.pool.get('account.report.report')
			acc_id = acc.search(cr, uid, [('code','in',code)])
			return reduce(lambda y,x=0: x.amount+y, acc.browse(cr, uid, acc_id, context),0)
		result = {}
		for rep in self.browse(cr, uid, ids, context):
			objdict = {
				'debit': _calc_debit,
				'credit': _calc_credit,
				'balance': _calc_balance,
				'report': _calc_report,
			}
			if field_name=='status':
				fld_name = 'expression_status'
			else:
				fld_name = 'expression'
			try:
				val = eval(getattr(rep, fld_name), objdict)
			except:
				val = 0.0
			if field_name=='status':
				if val<-1:
					result[rep.id] = 'very bad'
				elif val<0:
					result[rep.id] = 'bad'
				elif val==0:
					result[rep.id] = 'normal'
				elif val<1:
					result[rep.id] = 'good'
				else:
					result[rep.id] = 'excellent'
			else:
				result[rep.id] =  val
		return result

	def onchange_parent_id(self, cr, uid, ids, parent_id):
		v={}
		if parent_id:
			acc=self.pool.get('account.report.report').browse(cr,uid,parent_id)
			v['type']=acc.type
			if int(acc.style) < 6:
				v['style'] = str(int(acc.style)+1)
		return {'value': v}

	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'active': fields.boolean('Active'),
		'sequence': fields.integer('Sequence'),
		'code': fields.char('Code', size=64, required=True),
		'type': fields.selection([
			('fiscal', 'Fiscal statement'),
			('indicator','Indicator'),
			('other','Others')],
			'Type', required=True),
		'expression': fields.char('Expression', size=240, required=True),
		'expression_status': fields.char('Status expression', size=240, required=True),
		'parent_id': fields.many2one('account.report.report', 'Parent'),
		'child_ids': fields.one2many('account.report.report', 'parent_id', 'Childs'),
		'note': fields.text('Note'),
		'amount': fields.function(_amount_get, method=True, string='Value'),
		'status': fields.function(_amount_get,
			method=True,
			type="selection",
			selection=[
				('very bad', 'Very Bad'),
				('bad', 'Bad'),
				('normal', ''),
				('good', 'Good'),
				('excellent', 'Excellent')
			],
			string='Status'),
		'style': fields.selection(_style, 'Style', required=True),
		'color_font' : fields.selection(_color, 'Font Color', help="Font Color for the report"),
		'color_back' : fields.selection(_color, 'Back Color')
	}
	_defaults = {
		'style': lambda *args: '5',
		'active': lambda *args: True,
		'type': lambda *args: 'indicator',
	}

	def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
		if not args:
			args=[]
		if not context:
			context={}
		ids = []
		if name:
			ids = self.search(cr, user, [('code','=',name)]+ args, limit=limit, context=context)
			if not ids:
				ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
		else:
			ids = self.search(cr, user, args, limit=limit, context=context)
		return self.name_get(cr, user, ids, context=context)

	_constraints = [
	#TODO Put an expression to valid expression and expression_status
	]
	_sql_constraints = [
		('code_uniq', 'unique (code)', 'The code of the report entry must be unique !')
	]

account_report()
