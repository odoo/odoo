# -*- coding: utf-8 -*-

import wizard
import datetime
import time
import pooler


form='''<?xml version="1.0"?>
<form string="Report Options">
    <field name="date_from" colspan="2" />
    <field name="holiday_type" colspan="2" />
    <field name="emp" colspan="4" invisible="True"/>
</form>'''

zero_form='''<?xml version="1.0"?>
<form string="Notification">
<label string="You have to select at least 1 Employee. Try again." colspan="4"/>
</form>'''

zero_fields={
}

class wizard_report(wizard.interface):
    def _check(self, cr, uid, data, context):
        data['form']['date_from']=time.strftime('%Y-%m-%d')
        data['form']['holiday_type']='Validated'
        data['form']['emp'] = data['ids']
        return data['form']

    def _checkemps(self, cr, uid, data, context):

        if len(data['form']['emp'][0][2])==0:
            return 'notify'
        else:
            return 'report'

    fields={
        'date_from':{
            'string':'From',
            'type':'date',
            'required':True,
        },
        'holiday_type':{'string':"Select Holiday Type",'type':'selection','selection':[('Validated','Validated'),('Confirmed','Confirmed'),('both','Both')]},
        'emp': {'string': 'Employee(s)', 'type': 'many2many', 'relation': 'hr.employee'},
    }

    states={
        'init':{
            'actions':[_check],
            'result':{'type':'form', 'arch':form, 'fields':fields, 'state':[('end', 'Cancel'), ('checkemp', 'Print')]}
        },
        'checkemp': {
            'actions': [],
            'result': {'type':'choice','next_state':_checkemps}
        },
        'notify': {
            'actions': [],
            'result': {'type':'form','arch':zero_form,'fields':zero_fields,'state':[('end','Ok')]}
        },
        'report':{
            'actions':[],
            'result':{'type':'print', 'report':'holidays.summary', 'state':'end'}
        }
    }
wizard_report('hr.holidays.summary.employee')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

