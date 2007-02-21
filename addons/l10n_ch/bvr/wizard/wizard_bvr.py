##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import wizard
import pooler
import re

def _bank_get(self, cr, uid, context={}):
	pool = pooler.get_pool(cr.dbname)
	partner_id = pool.get('res.users').browse(cr,uid,[uid])[0].company_id.partner_id
	obj = pool.get('res.partner.bank')
	ids = obj.search(cr, uid, [('partner_id','=',partner_id.id)])
	res = obj.read(cr, uid, ids, ['active', 'name'], context)
	res = [(r['id'], r['name']) for r in res]
	return res 

check_form = """<?xml version="1.0"?>
<form string="BVR Print">
	<separator colspan="4" string="BVR Infos" />
	<field name="bank"/>
</form>
"""

check_fields = {
	'bank' : {
		'string':'Bank Account',
		'type':'selection',
		'selection':_bank_get,
		'required': True,
	},
}

def _check(self, cr, uid, data, context):
	for invoice in pooler.get_pool(cr.dbname).get('account.invoice').browse(cr, uid, data['ids'], context):
		bank = pooler.get_pool(cr.dbname).get('res.partner.bank').browse(cr, uid, data['form']['bank'], context)
		if not data['form']['bank']:
			raise wizard.except_wizard('UserError','No bank specified !')
		if not re.compile('[0-9][0-9]-[0-9]{3,6}-[0-9]').match(bank.bvr_number or ''):
			raise wizard.except_wizard('UserError','Your bank BVR number should be of the form 0X-XXX-X !\nPlease check your company information.')
		if bank.bank_code and not re.compile('[0-9A-Z]{8,11}$').match(bank.bank_code):
			raise wizard.except_wizard('UserError','Your bank code must be a number !\nPlease check your company information.')
	return {}

class wizard_report(wizard.interface):
	states = {
		'init':{
			'actions' : [],
			'result' : {
				'type' : 'form',
				'arch' : check_form,
				'fields' : check_fields,
				'state' : [('end', 'Cancel'),('bvr_print', 'Print') ]
			}
		},
		'bvr_print': {
			'actions': [_check], 
			'result': {'type':'print', 'report':'l10n_ch.bvr', 'state':'end'}
		}
	}
wizard_report('l10n_ch.bvr.check')


