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
import pooler

def _event_registration(self, cr, uid, data, context):
    event_id = data['id']
    cr.execute('SELECT section_id FROM event_event WHERE id = %s', (event_id, ))
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

