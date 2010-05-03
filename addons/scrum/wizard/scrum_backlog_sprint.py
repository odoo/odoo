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

class backlog_sprint_assign(osv.osv_memory):
    _name = 'backlog.assign.sprint'
    _description = 'Assign sprint to backlogs'
    _columns = {
        'sprint_id': fields.many2one('scrum.sprint', 'Sprint Name', required=True),
        'state_open': fields.boolean('Set Open', help="Change the state of product backlogs to open if its in draft state"),
        'convert_to_task': fields.boolean('Convert To Task', help="Create Task for Product Backlog")
               }
    _defaults = {
         'state_open': True,
         'convert_to_task': True,
                 }

    def assign_sprint(self, cr, uid, ids, context=None):
        backlog_obj = self.pool.get('scrum.product.backlog')
        task = self.pool.get('project.task')
        backlog_ids = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [], context=context)[0]
        for backlog in backlog_obj.browse(cr, uid, context['active_ids'], context=context):
            backlog_ids.append(backlog.id)
            if data['convert_to_task']:
                task.create(cr, uid, {
                    'product_backlog_id': backlog.id,
                    'name': backlog.name,
                    'description': backlog.note,
                    'project_id': backlog.project_id.id,
                    'user_id': False,
                    'planned_hours':backlog.planned_hours,
                    'remaining_hours':backlog.expected_hours,
                })
            if data['state_open'] and backlog.state == "draft":
                backlog_obj.write(cr, uid, backlog.id, {'state':'open'})
        backlog_obj.write(cr, uid, backlog_ids, {'sprint_id': data['sprint_id']}, context=context)
        return {}

backlog_sprint_assign()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: