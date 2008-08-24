# -*- encoding: utf-8 -*-
import wizard
import time
import datetime
import pooler

form = """<?xml version="1.0"?>
<form string="Select Information">
    <field name="date1"/>
    <field name="date2"/>
    <field name="ref" colspan="4"/>
    <field name="journal_ids" colspan="4"/>
    <field name="empty_line"/>
</form>"""

fields = {
    'date1': {'string':'Start Date', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-01-01')},
    'date2': {'string':'End Date', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-%m-%d')},
    'journal_ids': {'string':'Analytic Journal', 'type':'many2many', 'relation':'account.analytic.journal'},
    'ref' :{'string':'Analytic Account Ref.', 'type':'many2one', 'relation':'account.analytic.account','required':True},
    'empty_line': {'string':'Dont show empty lines', 'type':'boolean', 'default': lambda *a:False},
}

class wizard_crossovered_analytic(wizard.interface):
    def _checklines(self, cr, uid, data, context):
        cr.execute('select account_id from account_analytic_line')
        res=cr.fetchall()
        acc_ids=[x[0] for x in res]

        obj_acc = pooler.get_pool(cr.dbname).get('account.analytic.account').browse(cr,uid,data['form']['ref'])
        name=obj_acc.name

        account_ids = pooler.get_pool(cr.dbname).get('account.analytic.account').search(cr, uid, [('parent_id', 'child_of', [data['form']['ref']])])

        flag = True
        for acc in account_ids:
            if acc in acc_ids:
                flag = False
                break

        if flag:
            raise wizard.except_wizard('User Error',"There are no Analytic lines related to Account '" + name +"'" )
        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel'),('print','Print')]},
        },
        'print': {
            'actions': [_checklines],
            'result': {'type':'print', 'report':'account.analytic.account.crossovered.analytic', 'state':'end'},
        },
    }

wizard_crossovered_analytic('wizard.crossovered.analytic')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

