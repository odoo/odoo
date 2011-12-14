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

from osv import fields, osv

class procurement_order(osv.osv):
    _name = "procurement.order"
    _inherit = "procurement.order"
    _columns = {
        'task_id': fields.many2one('project.task', 'Task'),
        'sale_line_id': fields.many2one('sale.order.line', 'Sale order line')
    }
    
    def check_task_done(self, cr, uid, ids, context=None):
        """ Checks if task is done or not.
        @return: True or False.
        """
        res = False
        for procurement in self.browse(cr, uid, ids, context=context):
            product = procurement.product_id
            if product.type<>'service':
                res = True
            if procurement.task_id and procurement.task_id.state in ('done', 'cancelled'):
                res = True
        return res

    def check_produce_service(self, cr, uid, procurement, context=None):    
        return True

    def _convert_qty_company_hours(self, cr, uid, procurement, context=None):
        product_uom = self.pool.get('product.uom')
        company_time_uom_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.project_time_mode_id.id
        if procurement.product_uom.id != company_time_uom_id:
            planned_hours = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, company_time_uom_id)
        else:
            planned_hours = procurement.product_qty
        return planned_hours

    def action_produce_assign_service(self, cr, uid, ids, context=None):
        project_task = self.pool.get('project.task')
        for procurement in self.browse(cr, uid, ids, context=context):
            project_id = False
            if procurement.product_id.project_id:
                project_id = procurement.product_id.project_id.id
            elif procurement.sale_line_id:
                project_id = procurement.sale_line_id.order_id.project_id.id
            
            planned_hours = self._convert_qty_company_hours(cr, uid, procurement, context=context)
            task_id = project_task.create(cr, uid, {
                'name': '%s:%s' % (procurement.origin or '', procurement.product_id.name),
                'date_deadline': procurement.date_planned,
                'planned_hours':planned_hours,
                'remaining_hours': planned_hours,
                'user_id': procurement.product_id.product_manager.id,
                'notes': procurement.note,
                'procurement_id': procurement.id,
                'description': procurement.note,
                'project_id':  project_id,
                'company_id': procurement.company_id.id,
            },context=context)
            self.write(cr, uid, [procurement.id], {'task_id':task_id, 'state': 'running'}, context=context)
        return task_id

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
