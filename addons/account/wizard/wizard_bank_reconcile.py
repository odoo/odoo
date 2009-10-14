# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard
from tools.translate import _

_journal_form = '''<?xml version="1.0"?>
<form string="%s">
    <field name="journal_id"/>
</form>''' % ('Bank reconciliation',)

_journal_fields = {
    'journal_id': {'string':'Journal', 'type':'many2one', 'relation':'account.journal', 'required':True},
}

def _action_open_window(self, cr, uid, data, context):
    form = data['form']
    cr.execute('select default_credit_account_id from account_journal where id=%s', (form['journal_id'],))
    account_id = cr.fetchone()[0]
    if not account_id:
        raise wizard.except_wizard(_('Error'), _('You have to define the bank account\nin the journal definition for reconciliation.'))
    return {
        'domain': "[('journal_id','=',%d), ('account_id','=',%d), ('state','<>','draft')]" % (form['journal_id'],account_id),
        'name': _('Standard Encoding'),

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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

