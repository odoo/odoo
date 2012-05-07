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
from osv import osv, fields
from tools.translate import _

class backlog_sprint_assign(osv.osv_memory):
    _name = 'project.scrum.backlog.assign.sprint'
    _description = 'Assign sprint to backlogs'
    _inherit = ['mail.thread']
    _columns = {
        'sprint_id': fields.many2one('project.scrum.sprint', 'Sprint', required=True, help="Select Sprint to assign backlog."),
        'state_open': fields.boolean('Open Backlog', help="Change the state of product backlogs to open if its in draft state"),
        'convert_to_task': fields.boolean('Convert To Task', help="Create Task for Product Backlog")
    }
    _defaults = {
         'state_open': True,
         'convert_to_task': True,
    }

    def assign_sprint(self, cr, uid, ids, context=None):
        backlog_obj = self.pool.get('project.scrum.product.backlog')
        sprint_obj = self.pool.get('project.scrum.sprint')
        task = self.pool.get('project.task')
        backlog_ids = []
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids,context=context)[0]
        for backlog in backlog_obj.browse(cr, uid, context['active_ids'], context=context):
            backlog_ids.append(backlog.id)
            if data.convert_to_task:
                task_id = task.create(cr, uid, {
                    'product_backlog_id': backlog.id,
                    'name': backlog.name,
                    'description': backlog.note,
                    'project_id': backlog.project_id.id,
                    'user_id': False,
                    'planned_hours':backlog.expected_hours,
                    'remaining_hours':backlog.expected_hours,
                })
                message = _("Product Backlog '%s' is converted into Task %d.")  %(backlog.name, task_id)
                self.log(cr, uid, backlog.id, message)
            if data.state_open and backlog.state == "draft":
                backlog_obj.write(cr, uid, backlog.id, {'state':'open'})
            sprint = sprint_obj.browse(cr, uid, data.sprint_id.id, context=context)
            message = _("Product Backlog '%s' is assigned to sprint %s") %(backlog.name, sprint.name)
            self.log(cr, uid, backlog.id, message)
        backlog_obj.write(cr, uid, backlog_ids, {'sprint_id': data.sprint_id.id}, context=context)
        return {'type': 'ir.actions.act_window_close'}

backlog_sprint_assign()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
