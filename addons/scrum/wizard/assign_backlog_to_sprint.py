# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import ir
from mx.DateTime import now
import pooler
import netsvc

bts_form = """<?xml version="1.0" ?>
<form string="Assign Sprint">
    <group>
    <field name="sprint_id" colspan="2"/>
    </group>
    <newline/>
    <separator colspan="2"/>
    <newline/>
    <group>
    <field name="state_open" colspan="1"/>
    <field name="convert_to_task" colspan="1"/>
    </group>
</form>"""

bts_fields = {
    'sprint_id' : {'string':'Sprint Name', 'type':'many2one', 'relation':'scrum.sprint', 'required':True},
    'state_open' : {'string':'Set Open', 'type':'boolean'},
    'convert_to_task' : {'string':'Convert To Task', 'type':'boolean'}
}

def _assign_sprint(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    backlog_obj = pool.get('scrum.product.backlog')
    task = pool.get('project.task')
    state_open = data['form']['state_open']
    convert_to_task = data['form']['convert_to_task']
    for backlog in backlog_obj.browse(cr, uid, data['ids'], context=context):
        backlog_obj.write(cr, uid, backlog.id, {'sprint_id':data['form']['sprint_id']}, context=context)
        if convert_to_task:
            task.create(cr, uid, {
                'product_backlog_id': backlog.id,
                'name': backlog.name,
                'description': backlog.note,
                'project_id': backlog.project_id.id,
                'user_id': False,
                'planned_hours':backlog.planned_hours,
                'remaining_hours':backlog.expected_hours,
            })
        if state_open:
            if backlog.state == "draft":
                backlog_obj.write(cr, uid, backlog.id, {'state':'open'})
    return {}

class wiz_bts(wizard.interface):
    states = {
        'init':{
            'actions': [],
            'result': {'type':'form', 'arch':bts_form, 'fields':bts_fields, 'state':[('end', 'Cancel'), ('assign', 'Assign Sprint')] },
        },
        'assign':{
            'actions': [],
            'result': {'type':'action', 'action': _assign_sprint, 'state':'end'},
        },
    }
wiz_bts('scrum.product.backlog.sprint.assign')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

