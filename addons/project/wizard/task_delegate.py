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

import wizard
from tools import email_send as email
import pooler
from tools.translate import _

ask_form = """<?xml version="1.0" ?>
<form string="Delegate this task to a user">
    <separator string="Delegated Task" colspan="4"/>
    <field name="user_id" colspan="4"/>
    <field name="planned_hours" colspan="4" widget="float_time"/>
    <field name="name" colspan="4"/>
    <field name="new_task_description"/>
    <separator string="Validation Task" colspan="4"/>
    <field name="planned_hours_me" colspan="4" widget="float_time"/>
    <field name="prefix" colspan="4"/>
    <field name="state" colspan="4"/>
</form>"""

ask_fields = {
    'name': {'string': 'Delegated Title', 'type': 'char', 'required': 'True', 'size':64, 'help':"New title of the task delegated to the user."},
    'prefix': {'string': 'Your Task Title', 'type': 'char', 'required': 'True', 'size':64, 'help':"New title of your own task to validate the work done."},
    'user_id': {'string':'Assign To', 'type':'many2one', 'relation': 'res.users', 'required':'True', 'help':"User you want to delegate this task to."},
    'new_task_description': {'string':'New Task Description', 'type':'text', 'help':"Reinclude the description of the task in the task of the user."},
    'planned_hours': {'string':'Planned Hours', 'type':'float', 'widget':'float_time', 'help':"Estimated time to close this task by the delegated user."},
    'planned_hours_me': {'string':'Hours to Validate', 'type':'float', 'widget':'float_time', 'help':"Estimated time for you to validate the work done by the user to whom you delegate this task."},
    'state': {'string':'Validation State', 'type':'selection', 'selection': [('pending','Pending'),('done','Done')], 'help':"New state of your own task. Pending will be reopened automatically when the delegated task is closed.", 'required':True},
}

class wizard_delegate(wizard.interface):
    def _do_assign(self, cr, uid, data, context):
        task_obj = pooler.get_pool(cr.dbname).get('project.task')
        task = task_obj.browse(cr, uid, data['id'], context)
        newname = data['form']['prefix'] or ''
        task_obj.copy(cr, uid, data['id'], {
            'name': data['form']['name'],
            'user_id': data['form']['user_id'],
            'planned_hours': data['form']['planned_hours'],
            'remaining_hours': data['form']['planned_hours'],
            'parent_id': data['id'],
            'state': 'open',
            'description': data['form']['new_task_description'] or '',
            'child_ids': [],
            'work_ids': []
        })
        task_obj.write(cr, uid, data['id'], {
            'remaining_hours': data['form']['planned_hours_me'],
            'name': newname
        })
        if data['form']['state']=='pending':
            task_obj.do_pending(cr, uid, [data['id']])
        else:
            task_obj.do_close(cr, uid, [data['id']])
        return {}

    def _ask_auto_complete(self, cr, uid, data, context):
        task_obj = pooler.get_pool(cr.dbname).get('project.task')
        task = task_obj.browse(cr, uid, data['id'], context)
        if task.name.startswith(_('CHECK: ')):
            newname = task.name.strip(_('CHECK: '))
        else:
            newname = task.name or ''
        return {
            'name': newname,
            'user_id': False,
            'planned_hours': task.remaining_hours,
            'planned_hours_me': 1.0,
            'prefix': _('CHECK: ')+ newname,
            'new_task_description': task.description,
            'state': 'pending'
        }

    states = {
        'init': {
            'actions': [_ask_auto_complete],
            'result': {'type':'form', 'arch':ask_form, 'fields':ask_fields, 'state':[
                ('end', 'Cancel'),
                ('valid', 'Validate')
            ]},
        },
        'valid': {
            'actions': [_do_assign],
            'result': {'type':'state', 'state':'end'},
        }
    }
wizard_delegate('project.task.delegate')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

