# -*- encoding: utf-8 -*-
import wizard
import pooler
import time

def _action_open_window(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    mod_obj = pool.get('ir.model.data')
    act_obj = pool.get('ir.actions.act_window')

    result = mod_obj._get_id(cr, uid, 'stock', 'action_move_form2')
    id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
    result = act_obj.read(cr, uid, [id])[0]
    location_id = data['ids'][0]

    domain = []
#    domain += [ '|' ,('location_id', '=', location_id) , ('location_dest_id', '=', location_id)]
    if data['form']['from']:
        domain += [('date_planned', '>=', data['form']['from'])]
    
    if data['form']['to']:
        domain += [('date_planned', '<=', data['form']['to'])]
    result['domain'] = str(domain)
#    result['context'] = str({'location_id': location_id })
    return result


class move_by_location(wizard.interface):
    
    form1 = '''<?xml version="1.0"?>
    <form string="View Stock Moves">
        <field name="from"/>
        <newline/>
        <field name="to"/>
    </form>'''
    
    form1_fields = {
             'from': {
                'string': 'From',
                'type': 'date',
        },
             'to': {
                'string': 'To',
                'type': 'date',
#                'default': lambda *a: time.strftime("%Y-%m-%d"),
        },
    }

    states = {
      'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, 'state': [ ('open', 'Open Moves'),('end', 'Cancel')]}
        },
    'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
    
move_by_location('stock.location.moves')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: