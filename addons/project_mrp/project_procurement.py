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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class procurement_order(osv.osv):
    _name = "procurement.order"
    _inherit = "procurement.order"
    _columns = {
        'task_id': fields.many2one('project.task', 'Task'),
        'sale_line_id': fields.many2one('sale.order.line', 'Sales order line')
    }

    def action_check_finished(self, cr, uid, ids):
        res = super(procurement_order, self).action_check_finished(cr, uid, ids)
        return res and self.check_task_done(cr, uid, ids)
    
    def check_task_done(self, cr, uid, ids, context=None):
        """ Checks if task is done or not.
        @return: True or False.
        """
        for p in self.browse(cr, uid, ids, context=context):
            if (p.product_id.type=='service') and (p.procure_method=='make_to_order') and p.task_id and (p.task_id.state not in ('done', 'cancelled')):
                return False
        return True

    def check_produce_service(self, cr, uid, procurement, context=None):
        return True

    def _convert_qty_company_hours(self, cr, uid, procurement, context=None):
        product_uom = self.pool.get('product.uom')
        company_time_uom_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.project_time_mode_id
        if procurement.product_uom.id != company_time_uom_id.id and procurement.product_uom.category_id.id == company_time_uom_id.category_id.id:
            planned_hours = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, company_time_uom_id.id)
        else:
            planned_hours = procurement.product_qty
        return planned_hours

    def _get_project(self, cr, uid, procurement, context=None):
        project_project = self.pool.get('project.project')
        project = procurement.product_id.project_id
        if not project and procurement.sale_line_id:
            # find the project corresponding to the analytic account of the sales order
            account = procurement.sale_line_id.order_id.project_id
            project_ids = project_project.search(cr, uid, [('analytic_account_id', '=', account.id)])
            projects = project_project.browse(cr, uid, project_ids, context=context)
            project = projects and projects[0] or False
        return project

    def action_produce_assign_service(self, cr, uid, ids, context=None):
        project_task = self.pool.get('project.task')
        for procurement in self.browse(cr, uid, ids, context=context):
            project = self._get_project(cr, uid, procurement, context=context)
            planned_hours = self._convert_qty_company_hours(cr, uid, procurement, context=context)
            task_id = project_task.create(cr, uid, {
                'name': '%s:%s' % (procurement.origin or '', procurement.product_id.name),
                'date_deadline': procurement.date_planned,
                'planned_hours': planned_hours,
                'remaining_hours': planned_hours,
                'partner_id': procurement.sale_line_id and procurement.sale_line_id.order_id.partner_id.id or False,
                'user_id': procurement.product_id.product_manager.id,
                'procurement_id': procurement.id,
                'description': procurement.name + '\n' + (procurement.note or ''),
                'project_id':  project and project.id or False,
                'company_id': procurement.company_id.id,
            },context=context)
            self.write(cr, uid, [procurement.id], {'task_id': task_id, 'state': 'running', 'message':_('Task created.')}, context=context)            
        self.project_task_create_note(cr, uid, ids, context=context)
        return task_id

    def project_task_create_note(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids, context=context):
            body = _("Task created")
            self.message_post(cr, uid, [procurement.id], body=body, context=context)

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
