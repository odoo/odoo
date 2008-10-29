# -*- encoding: utf-8 -*-
import wizard
import pooler

def _event_tasks(self, cr, uid, data, context):
    event_id = data['id']
    cr.execute('''SELECT project_id FROM event_event WHERE id = %d '''% (event_id, ))
    res = cr.fetchone()
    if not res[0]:
        raise wizard.except_wizard('Error !', 'No project defined for this event.\nYou can create one with the retro-planning button !')
    value = {
        'domain': [('project_id', '=', res[0])],
        'name': 'Tasks',
        'view_type': 'form',
        'view_mode': 'tree,form,calendar',
        'res_model': 'project.task',
        'context': { },
        'type': 'ir.actions.act_window'
    }
    return value

class wizard_event_tasks(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _event_tasks,
                'state': 'end'
            }
        },
    }
wizard_event_tasks("wizard_event_tasks")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

