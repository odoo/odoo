# -*- encoding: utf-8 -*-
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

