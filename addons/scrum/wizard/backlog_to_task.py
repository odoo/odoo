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
import ir
from mx.DateTime import now
import pooler
import netsvc

btt_form = """<?xml version="1.0" ?>
<form string="Create Tasks">
    <field name="user_id"/>
</form>"""

btt_fields = {
    'user_id' : {'string':'Assign To', 'type':'many2one', 'relation':'res.users'},
}

def _do_create(self, cr, uid, data, context):
    backlogs = pooler.get_pool(cr.dbname).get('scrum.product.backlog').browse(cr, uid, data['ids'])
    ids = []
    for backlog in backlogs:
        task = pooler.get_pool(cr.dbname).get('scrum.task')
        ids.append(task.create(cr, uid, {
            'product_backlog_id': backlog.id,
            'name': backlog.name,
            'description': backlog.note,
            'project_id': backlog.project_id.id,
            'user_id': (backlog.user_id and backlog.user_id.id) or uid,
            'priority': backlog.priority,
            'planned_hours': backlog.planned_hours
        }))

    value = {
        'domain': "[('product_backlog_id','in',["+','.join(map(str,data['ids']))+"])]",
        'name': 'Open Backlog Tasks',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'scrum.task',
        'view_id': False,
        'type': 'ir.actions.act_window'
    }
    return value

class wiz_btt(wizard.interface):
    states = {
        'init':{
            'actions': [],
            'result': {'type':'form', 'arch':btt_form, 'fields':btt_fields, 'state':[('end', 'Cancel'), ('create', 'Create Tasks')] },
        },
        'create':{
            'actions': [],
            'result': {'type':'action', 'action': _do_create, 'state':'end'},
        },
    }
wiz_btt('scrum.product.backlog.task.create')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

