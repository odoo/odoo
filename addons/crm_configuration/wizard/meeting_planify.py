# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler

from tools.translate import _

case_form = """<?xml version="1.0"?>
<form string="Planify Meeting">
    <field name="date"/>
    <field name="duration" widget="float_time"/>
    <label string="Note that you can also use the calendar view to graphically schedule your next meeting." colspan="4"/>
</form>"""

case_fields = {
    'date': {'string': 'Meeting date', 'type': 'datetime', 'required': 1},
    'duration': {'string': 'Duration (Hours)', 'type': 'float', 'required': 1}
}


class make_meeting(wizard.interface):
    def _selectPartner(self, cr, uid, data, context):
        case_obj = pooler.get_pool(cr.dbname).get('crm.case')
        case = case_obj.browse(cr, uid, data['id'])
        return {'date': case.date, 'duration': case.duration or 2.0}

    def _makeMeeting(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)

        case_obj = pool.get('crm.case')
        new_id = case_obj.write(cr, uid, data['id'], {
            'date': data['form']['date'],
            'duration': data['form']['duration']
        }, context=context)
        case_obj._history(cr, uid, case_obj.browse(cr, uid, [data['id']]), _('meeting'))
        return {}

    states = {
        'init': {
            'actions': [_selectPartner],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state' : [('end', 'Cancel','gtk-cancel'),('order', 'Set Meeting','gtk-go-forward')]}
        },
        'order': {
            'actions': [],
            'result': {'type': 'action', 'action': _makeMeeting, 'state': 'end'}
        }
    }

make_meeting('crm.case.meeting')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
