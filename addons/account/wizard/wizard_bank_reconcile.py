##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

_journal_form = '''<?xml version="1.0"?>
<form string="%s">
	<field name="journal_id"/>
</form>''' % ('Bank reconciliation',)

_journal_fields = {
	'journal_id': {'string':'Journal', 'type':'many2one', 'relation':'account.journal', 'required':True},
}

def _action_open_window(self, cr, uid, data, context):
	form = data['form']
	cr.execute('select default_credit_account_id from account_journal where id=%d', (form['journal_id'],))
	account_id = cr.fetchone()[0]
	if not account_id:
		raise Exception, 'You have to define the bank account\nin the journal definition for reconciliation.'
	return {
		'domain': "[('journal_id','=',%d), ('account_id','=',%d), ('state','<>','draft')]" % (form['journal_id'],account_id),
		'name': 'Saisie Standard',
		'view_type': 'form',
		'view_mode': 'tree,form',
		'res_model': 'account.move.line',
		'view_id': False,
		'context': "{'journal_id':%d}" % (form['journal_id'],),
		'type': 'ir.actions.act_window'
	}

class wiz_journal(wizard.interface):
	states = {
		'init': {
			'actions': [],
			'result': {'type': 'form', 'arch':_journal_form, 'fields':_journal_fields, 'state':[('end','Cancel'),('open','Open for bank reconciliation')]}
		},
		'open': {
			'actions': [],
			'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
		}
	}
wiz_journal('account.move.bank.reconcile')

