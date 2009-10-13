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
import pooler
import netsvc

form = '''<?xml version="1.0"?>
<form string="Open Invoice">
    <label string="Are you sure you want to open this invoice ?"/>
    <newline/>
    <label string="(Invoice should be unreconciled if you want to open it)"/>
</form>'''

fields = {
}

def _change_inv_state(self, cr, uid, data, context):
    pool_obj = pooler.get_pool(cr.dbname)
    data_inv = pool_obj.get('account.invoice').browse(cr, uid, data['ids'][0])
    if data_inv.reconciled:
        raise wizard.except_wizard(_('Warning'), _('Invoice is already reconciled'))
    wf_service = netsvc.LocalService("workflow")
    res = wf_service.trg_validate(uid, 'account.invoice', data['ids'][0], 'open_test', cr)
    return {}

class wiz_state_open(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':form, 'fields':fields, 'state':[('end','No','gtk-no'),('yes','Yes','gtk-yes')]}
        },
        'yes': {
            'actions': [_change_inv_state],
            'result': {'type':'state', 'state':'end'}
        }
    }
wiz_state_open('account.wizard_paid_open')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
