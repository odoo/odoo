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
import netsvc

def _invoice_confirm(self, cr, uid, data, context):
    wf_service = netsvc.LocalService('workflow')
    for id in data['ids']:
        wf_service.trg_validate(uid, 'account.invoice', id, 'invoice_open', cr)
    return {}

class wizard_invoice_confirm(wizard.interface):
    states = {
        'init': {
            'actions': [_invoice_confirm], 
            'result': {'type':'state', 'state':'end'}
        }
    }
wizard_invoice_confirm('account.invoice.state.confirm')


def _invoice_cancel(self, cr, uid, data, context):
    wf_service = netsvc.LocalService('workflow')
    for id in data['ids']:
        wf_service.trg_validate(uid, 'account.invoice', id, 'invoice_cancel', cr)
    return {}

class wizard_invoice_cancel(wizard.interface):
    states = {
        'init': {
            'actions': [_invoice_cancel], 
            'result': {'type':'state', 'state':'end'}
        }
    }
wizard_invoice_cancel('account.invoice.state.cancel')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

