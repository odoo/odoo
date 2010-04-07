# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class account_vat_declaration(osv.osv_memory):
	_name = 'account.vat.declaration'
	_description = 'Account Vat Declaration'

	_columns = {
        'based_on': fields.selection([('invoices','Invoices'),
									 ('payments','Payments'),],
									  'Based On', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
		'periods': fields.many2many('account.period', 'vat_period_rel', 'vat_id', 'period_id', 'Periods', help="All periods if empty"),
		}

	def _get_company(self, cr, uid, ids, context={}):
		user_obj = self.pool.get('res.users')
		company_obj = self.pool.get('res.company')
		user = user_obj.browse(cr, uid, uid, context=context)
		if user.company_id:
			return user.company_id.id
		else:
			return company_obj.search(cr, uid, [('parent_id', '=', False)])[0]

	_defaults = {
	        'based_on': lambda *a: 'invoices',
	        'company_id': _get_company
	    }

	def create_vat(self, cr, uid, ids, context={}):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
  		datas['model'] = 'account.tax.code'
		datas['form'] = self.read(cr, uid, ids)[0]
		print "datasssss", datas, datas['form']
		return {
			'type': 'ir.actions.report.xml',
			'report_name': 'account.vat.declaration',
			'datas': datas,
			}

account_vat_declaration()

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
