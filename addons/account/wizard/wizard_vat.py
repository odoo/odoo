# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import wizard
import pooler

dates_form = '''<?xml version="1.0"?>
<form string="Select period">
	<field name="company_id"/>
	<newline/>
	<field name="based_on"/>
	<field name="periods" colspan="4"/>

	
</form>'''

dates_fields = {
	'company_id': {'string': 'Company', 'type': 'many2one',
		'relation': 'res.company', 'required': True},
	'based_on':{'string':'Base on', 'type':'selection', 'selection':[
			('invoices','Invoices'),
			('payments','Payments'),
			], 'required':True, 'default': lambda *a: 'invoices'},
	'periods': {'string': 'Periods', 'type': 'many2many', 'relation': 'account.period', 'help': 'All periods if empty'},

}


class wizard_report(wizard.interface):

	def _get_defaults(self, cr, uid, data, context):
		pool = pooler.get_pool(cr.dbname)
		period_obj = pool.get('account.period')

		user = pool.get('res.users').browse(cr, uid, uid, context=context)
		if user.company_id:
			company_id = user.company_id.id
		else:
			company_id = pool.get('res.company').search(cr, uid,
					[('parent_id', '=', False)])[0]
		data['form']['company_id'] = company_id

		return data['form']

	states = {
		'init': {
			'actions': [_get_defaults],
			'result': {
				'type': 'form',
				'arch': dates_form,
				'fields': dates_fields,
				'state': [
					('end', 'Cancel'),
					('report', 'Print VAT Decl.')
				]
			}
		},
		'report': {
			'actions': [],
			'result': {
				'type': 'print',
				'report': 'account.vat.declaration',
				'state':'end'
			}
		}
	}

wizard_report('account.vat.declaration')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
