# -*- encoding: utf-8 -*-
import time
import wizard

dates_form = '''<?xml version="1.0"?>
<form string="Select Dates Period">
    <field name="date_from"/>
    <field name="date_to"/>
</form>'''

dates_fields = {
    'date_from': {'string':'Start of period', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-01-01')},
    'date_to': {'string':'End of period', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-%m-%d')}
}

class wizard_report(wizard.interface):

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':dates_form, 'fields':dates_fields, 'state':[('end','Cancel'),('report','Print')]}
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'account.analytic.account.budget', 'state':'end'}
        }
    }
wizard_report('wizard.analytic.account.budget.report')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

