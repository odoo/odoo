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
import time
import datetime
import pooler

invoice_form = """<?xml version="1.0"?>
<form string="Select Message">
    <field name="message"/>
</form>"""

invoice_fields = {
    'message': {'string': 'Message', 'type': 'many2one', 'relation': 'notify.message', 'required': True},
   }

class wizard_report(wizard.interface):

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':invoice_form, 'fields':invoice_fields, 'state':[('end','Cancel'),('print','Print')]},
        },
        'print': {
            'actions': [],
            'result': {'type':'print', 'report':'notify_account.invoice', 'state':'end'},
        },
    }

wizard_report('wizard.notify_message')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

