# -*- encoding: utf-8 -*-

import wizard
import netsvc
import ir
import pooler

cancel_form = """<?xml version="1.0"?>
<form string="Cancel Order">
    <label string="Are you sure you want to cancel this order ?"/>
</form>"""


cancel_fields = {
}

def _cancel(self,cr,uid,data,context):
    return pooler.get_pool(cr.dbname).get('lunch.order').lunch_order_cancel(cr,uid,data['ids'],context)

class order_cancel(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':cancel_form, 'fields':cancel_fields, 'state':[('end','No'),('cancel','Yes')]}
        },
        'cancel': {
            'actions': [_cancel],
            'result': {'type':'state', 'state':'end'}
        }
    }
order_cancel('lunch.order.cancel')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

