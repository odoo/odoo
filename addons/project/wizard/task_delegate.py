# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
from tools import email_send as email
import pooler

ask_form = """<?xml version="1.0" ?>
<form string="Delegate this task to a user">
    <separator string="Delegated Task" colspan="4"/>
    <field name="user_id" colspan="4"/>
    <field name="planned_hours" colspan="4"/>
    <field name="name" colspan="4"/>
    <field name="include_info"/>
    <separator string="Validation Task" colspan="4"/>
    <field name="planned_hours_me" colspan="4"/>
    <field name="prefix" colspan="4"/>
    <field name="state" colspan="4"/>
</form>"""

ask_fields = {
    'name': {'string': 'Title', 'type': 'char', 'required': 'True', 'size':64},
    'prefix': {'string': 'Prefix of Task', 'type': 'char', 'required': 'True', 'size':64},
    'user_id': {'string':'Assign To', 'type':'many2one', 'relation': 'res.users', 'required':'True'},
    'include_info': {'string':'Copy Description', 'type':'boolean'},
    'planned_hours': {'string':'Planned Hours', 'type':'float', 'widget':'float_time'},
    'planned_hours_me': {'string':'Hours to Validate', 'type':'float', 'widget':'float_time'},
    'state': {'string':'Validation State', 'type':'selection', 'selection': [('pending','Pending'),('done','Done')]},
}

class wizard_delegate(wizard.interface):
    def _do_assign(self, cr, uid, data, context):
        task_obj = pooler.get_pool(cr.dbname).get('project.task')
        task = task_obj.browse(cr, uid, data['id'], context)
        newname = task.name
        if not task.name.startswith(data['form']['prefix'] or '++'):
            newname = (data['form']['prefix'] or '')+task.name
        task_obj.copy(cr, uid, data['id'], {
            'name': data['form']['name'],
            'user_id': data['form']['user_id'],
            'planned_hours': data['form']['planned_hours'],
            'remaining_hours': data['form']['planned_hours'],
            'parent_id': data['id'],
            'state': 'open',
            'description': data['form']['include_info'] and task.description or '',
            'child_ids': []
        })
        task_obj.write(cr, uid, data['id'], {
            'planned_hours': data['form']['planned_hours_me'],
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
        return {
            'name':task.name,
            'user_id': False,
            'planned_hours': task.planned_hours,
            'planned_hours_me': task.planned_hours / 5.0,
            'prefix': 'CHECK: ',
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

