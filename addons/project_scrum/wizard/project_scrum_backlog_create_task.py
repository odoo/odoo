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

class backlog_create_task(osv.osv_memory):
    _name = 'project.scrum.backlog.create.task'
    _description = 'Create Tasks from Product Backlogs'
    _columns = {
        'user_id': fields.many2one('res.users', 'Assign To', help="Responsible user who can work on task")
    }

    def do_create(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        task = self.pool.get('project.task')
        backlog_id = self.pool.get('project.scrum.product.backlog')
        document_pool = self.pool.get('ir.attachment')
        ids_task = []

        data = self.read(cr, uid, ids, [], context=context)[0]
        data['user_id'] = data['user_id'][0]

        backlogs = backlog_id.browse(cr, uid, context['active_ids'], context=context)
        result = mod_obj._get_id(cr, uid, 'project', 'view_task_search_form')
        id = mod_obj.read(cr, uid, result, ['res_id'])

        for backlog in backlogs:
            task_id = task.create(cr, uid, {
                'product_backlog_id': backlog.id,
                'name': backlog.name,
                'description': backlog.note,
                'project_id': backlog.project_id.id,
                'user_id': data['user_id'] or False,
                'planned_hours': backlog.expected_hours,
                'remaining_hours':backlog.expected_hours,
                'sequence':backlog.sequence,
            })
            document_ids = document_pool.search(cr, uid, [('res_id', '=', backlog.id), ('res_model', '=', backlog_id._name)])
            for document_id in document_ids:
                document_pool.copy(cr, uid, document_id, default={'res_id':task_id, 'res_model':task._name})
            ids_task.append(task_id)
        return {
            'domain': "[('product_backlog_id','in',["+','.join(map(str, context['active_ids']))+"])]",
            'name': 'Tasks',
            'res_id': ids_task,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'project.task',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id'],
        }

backlog_create_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
