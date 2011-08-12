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

from osv import fields, osv, orm

import tools

class procurement_order(osv.osv):
    _name = "procurement.order"
    _inherit = "procurement.order"
    _columns = {
        'task_id': fields.many2one('project.task', 'Task')
    }
    def check_produce_service(self, cr, uid, procurement, context=None):
        return True

    def action_produce_assign_service(self, cr, uid, ids, context=None):
        line_pool=self.pool.get('sale.order.line')
        project_pool=self.pool.get('project.project')
        for procurement in self.browse(cr, uid, ids, context=context):
            project_id = False
            line_ids = line_pool.search(cr, uid , [('procurement_id', '=', procurement.id)])
            order_lines = line_pool.browse(cr, uid, line_ids)
            for line in order_lines:
                if line.product_id and  line.product_id.project_id:            
                    project_id = line.product_id.project_id.id
                if not project_id and line.order_id.project_id:
                    project_id = project_pool.search(cr, uid , [('name', '=', line.order_id.project_id.name)])
                    project_id = project_id and project_id[0] or False
            self.write(cr, uid, [procurement.id], {'state': 'running'})
            planned_hours = procurement.product_qty
            task_id = self.pool.get('project.task').create(cr, uid, {
                'name': '%s:%s' % (procurement.origin or '', procurement.product_id.name),
                'date_deadline': procurement.date_planned,
                'planned_hours':planned_hours,
                'remaining_hours': planned_hours,
                'user_id': procurement.product_id.product_manager.id,
                'notes': procurement.note,
                'procurement_id': procurement.id,
                'description': procurement.note,
                'date_deadline': procurement.date_planned,
                'project_id':  project_id,
                'state': 'draft',
                'company_id': procurement.company_id.id,
            },context=context)
            self.write(cr, uid, [procurement.id],{'task_id':task_id}) 
        return task_id

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
