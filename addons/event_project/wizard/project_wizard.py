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

#
# Order Point Method:
#   - Order if the virtual stock of today is bellow the min of the defined order point
#

import wizard
import pooler

import time

parameter_form = '''<?xml version="1.0"?>
<form string="Event" colspan="4">
    <field name="project_id"
/>
</form>'''

parameter_fields = {
    'project_id': {'string':'Project', 'type':'many2one', 'required':True, 'relation':'project.project', 'domain': [('active','<>',False)]},
}

def _create_duplicate(self, cr, uid, data, context):
    event_obj=pooler.get_pool(cr.dbname).get('event.event')
    project_obj = pooler.get_pool(cr.dbname).get('project.project')
    duplicate_project_id= project_obj.copy(cr, uid,data['form']['project_id'], {'active': True})
    project_obj.write(cr, uid, [duplicate_project_id], {'name': "copy of " + project_obj.browse(cr, uid, duplicate_project_id, context).name , 'date_start':time.strftime('%Y-%m-%d'),'date_end': event_obj.browse(cr, uid, [data['id']])[0].date_begin[0:10] })
    event_obj.write(cr, uid, [data['id']], {'project_id': duplicate_project_id })
    return {}

class wizard_event_project(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':parameter_form, 'fields': parameter_fields, 'state':[('end','Cancel'),('done', 'Ok')]}

        },
        'done':{
                'actions':[_create_duplicate],
                'result' : {'type':'state', 'state':'end'}
                }
    }
wizard_event_project('event.project')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

