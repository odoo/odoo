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
        task_obj = self.pool.get('project.task')
        for procurement in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [procurement.id], {'state': 'running'})
            planned_hours = procurement.product_qty
            proj_uom = procurement.company_id.project_time_mode_id
            if proj_uom and not proj_uom.name == procurement.product_uom.name:
                if proj_uom.category_id == procurement.product_uom.category_id:
                    planned_hours = procurement.product_qty * procurement.product_uom.factor_inv # Converting to the referring UoM
                    planned_hours *= proj_uom.factor # Converting to the Project UoM
            
            task_id = task_obj.create(cr, uid, {
                'name': '%s:%s' % (procurement.origin or '', procurement.name),
                'date_deadline': procurement.date_planned,
                'planned_hours':planned_hours,
                'remaining_hours': planned_hours,
                'user_id': procurement.product_id.product_manager.id,
                'notes': procurement.note,
                'procurement_id': procurement.id,
                'description': procurement.note,
                'date_deadline': procurement.date_planned,
                'project_id': procurement.product_id.project_id and procurement.product_id.project_id.id or False,
                'state': 'draft',
                'company_id': procurement.company_id.id,
            },context=context)
            self.write(cr, uid, [procurement.id],{'task_id':task_id}) 
        return task_id

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
