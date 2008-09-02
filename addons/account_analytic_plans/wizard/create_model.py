# -*- encoding: utf-8 -*-
import wizard
import time
import netsvc
import pooler

info = '''<?xml version="1.0"?>
<form string="Distribution Model Saved">
    <label string="This distribution model has been saved.\nYou will be able to reuse it later."/>
</form>'''

def activate(self, cr, uid, data, context):
    plan_obj = pooler.get_pool(cr.dbname).get('account.analytic.plan.instance')
    if data['id']:
        plan = plan_obj.browse(cr, uid, data['id'], context)
        if (not plan.name) or (not plan.code):
            raise wizard.except_wizard('Error', 'Please put a name and a code before saving the model !')
        pids  =  pooler.get_pool(cr.dbname).get('account.analytic.plan').search(cr, uid, [], context=context)
        if (not pids):
            raise wizard.except_wizard('Error', 'No analytic plan defined !')
        plan_obj.write(cr,uid,[data['id']],{'plan_id':pids[0]})
        return 'info'
    else:
        return 'endit'


class create_model(wizard.interface):

    states = {
        'init': {
            'actions': [],
            'result': {'type':'choice','next_state':activate}
        },
        'info': {
            'actions': [],
            'result': {'type':'form', 'arch':info, 'fields':{}, 'state':[('end','OK')]}
        },
        'endit': {
            'actions': [],
            'result': {'type':'form', 'arch':'', 'fields':{}, 'state':[('end','OK')]} #FIXME: check
        },
    }
create_model('create.model')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

