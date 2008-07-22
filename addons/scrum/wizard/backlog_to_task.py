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
            'priority': backlog.priority
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

# vim:noexpandtab:tw=0
