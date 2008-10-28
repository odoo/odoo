# -*- encoding: utf-8 -*-
import wizard
import pooler

def _event_registration(self, cr, uid, data, context):
    event_id = data['id']
    cr.execute(''' SELECT section_id FROM event_event WHERE id = %d '''% (event_id, ))
    res = cr.fetchone()
    value = {
        'domain': [('section_id', '=', res[0])],
        'name': 'Event registration',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'event.registration',
        'context': { },
        'type': 'ir.actions.act_window'
    }
    return value

class wizard_event_registration(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _event_registration,
                'state': 'end'
            }
        },
    }
wizard_event_registration("wizard_event_registration")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

