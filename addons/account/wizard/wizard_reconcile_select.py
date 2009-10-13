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

import wizard
from tools.translate import _


_journal_form = '''<?xml version="1.0"?>
<form string="%s">
    <field name="account_id"/>
</form>''' % ('Reconciliation',)

_journal_fields = {
    'account_id': {'string':'Account', 'type':'many2one', 'relation':'account.account','domain': [('reconcile','=',1)], 'required':True},
}

def _action_open_window(self, cr, uid, data, context):
    return {
        'domain': "[('account_id','=',%d),('reconcile_id','=',False),('state','<>','draft')]" % data['form']['account_id'],
        'name': _('Reconciliation'),
        'view_type': 'form',
        'view_mode': 'tree,form',
        'view_id': False,
        'res_model': 'account.move.line',
        'type': 'ir.actions.act_window'
    }

class wiz_rec_select(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_journal_form, 'fields':_journal_fields, 'state':[('end','Cancel'),('open','Open for reconciliation')]}
        },
        'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
wiz_rec_select('account.move.line.reconcile.select')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

