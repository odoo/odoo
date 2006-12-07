##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

_transaction_form = '''<?xml version="1.0"?>
<form string="Close Journal">
	<separator string="Close the journal" colspan="4"/>
	<field name="debit"/>
	<field name="credit"/>
	<field name="count"/>
	<separator string="Are you sure ?" colspan="4"/>
	<field name="sur"/>
</form>'''

_transaction_fields = {
	'credit': {'string':'Credit amount', 'type':'float', 'readonly':True},
	'debit': {'string':'Debit amount', 'type':'float', 'readonly':True},
	'count': {'string':'Count', 'type':'float', 'readonly':True},
	'sur': {'string':'Check this box', 'type':'boolean'},
}

def _data_load(self, cr, uid, data, context):
	data['form']['credit'] = 0
	data['form']['debit'] = 0
	data['form']['count'] = 0
	for id in data['ids']:
		cr.execute('select sum(credit), sum(debit), count(*) from account_move_line where journal_id=%d and period_id=%d', result)
		result = cr.fetchone()
		data['form']['credit'] += result[0] or 0.0
		data['form']['debit'] += result[1] or 0.0
		data['form']['count'] += result[2] or 0.0
	return data['form']

def _data_save(self, cr, uid, data, context):
	if data['form']['sur']:
		for id in data['ids']:
			cr.execute('select journal_id,period_id from account_journal_period where id=%d', (id,))
			result = cr.fetchone()
			cr.execute('delete from account_move_line where journal_id=%d and period_id=%d and state=\'draft\'', result)
			cr.execute('update account_journal_period set state=%s where id=%d', ('done', id))
	return {}

class wiz_journal_close(wizard.interface):
	states = {
		'init': {
			'actions': [_data_load],
			'result': {'type': 'form', 'arch':_transaction_form, 'fields':_transaction_fields, 'state':[('end','Cancel'),('close','Close Journal')]}
		},
		'close': {
			'actions': [_data_save],
			'result': {'type': 'state', 'state':'end'}
		}
	}
wiz_journal_close('account.journal.period.close')

