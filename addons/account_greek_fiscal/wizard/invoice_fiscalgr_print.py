# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2008 P. Christeas. All Rights Reserved
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
import time
import datetime
import pooler

# *-* this code is still useless..

invoice_form = """<?xml version="1.0"?>
<form string="Confirm">
    <label string="Please confirm if you really want to issue this invoice."/>
    <label string="After issuing, it becomes a legal document."/>
</form>"""

invoice_fields = { }

def _invoice_print(self, cr, uid, data, context):
    wf_service = netsvc.LocalService('workflow')
    for id in data['ids']:
	common.message("aaa: %d"%id)
        #wf_service.trg_validate(uid, 'account.invoice', id, 'invoice_open', cr)
    return {}

class wizard_report(wizard.interface):

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':invoice_form, 'fields':invoice_fields, 
	    	'state':[('end','Cancel'),('print','Print')]},
        },
        'print': {
            'actions': [_invoice_print],
            'result': {'type':'state' , 'state':'end'},
        },
    }

wizard_report('wizard.fiscalgr.invoice_print')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

