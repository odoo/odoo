# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _

class procurement_order(osv.osv):
    _name = "procurement.order"
    _inherit = "procurement.order"
    _columns = {
        'task_id': fields.many2one('project.task', 'Task', copy=False),
    }

    def _is_procurement_task(self, cr, uid, procurement, context=None):
        return procurement.product_id.type == 'service' and procurement.product_id.auto_create_task or False

    def _assign(self, cr, uid, procurement, context=None):
        res = super(procurement_order, self)._assign(cr, uid, procurement, context=context)
        if not res:
            #if there isn't any specific procurement.rule defined for the product, we may want to create a task
            if self._is_procurement_task(cr, uid, procurement, context=context):
                return True
        return res

    def _run(self, cr, uid, procurement, context=None):
        if self._is_procurement_task(cr, uid, procurement, context=context) and not procurement.task_id:
            #create a task for the procurement
            return self._create_service_task(cr, uid, procurement, context=context)
        return super(procurement_order, self)._run(cr, uid, procurement, context=context)

    def _check(self, cr, uid, procurement, context=None):
        if self._is_procurement_task(cr, uid, procurement, context=context):
            return procurement.task_id and procurement.task_id.stage_id.closed or False
        return super(procurement_order, self)._check(cr, uid, procurement, context=context)

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

    def _create_service_task(self, cr, uid, procurement, context=None):
        project_task = self.pool.get('project.task')
        project = self._get_project(cr, uid, procurement, context=context)
        planned_hours = self._convert_qty_company_hours(cr, uid, procurement, context=context)
        task_id = project_task.create(cr, uid, {
            'name': '%s:%s' % (procurement.origin or '', procurement.product_id.name),
            'date_deadline': procurement.date_planned,
            'planned_hours': planned_hours,
            'remaining_hours': planned_hours,
            'partner_id': procurement.sale_line_id and procurement.sale_line_id.order_id.partner_id.id or procurement.partner_dest_id.id,
            'user_id': procurement.product_id.product_manager.id,
            'procurement_id': procurement.id,
            'description': procurement.name + '\n',
            'project_id': project and project.id or False,
            'company_id': procurement.company_id.id,
        },context=context)
        self.write(cr, uid, [procurement.id], {'task_id': task_id}, context=context)
        self.project_task_create_note(cr, uid, [procurement.id], context=context)
        return task_id

    def project_task_create_note(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids, context=context):
            body = _("Task created")
            self.message_post(cr, uid, [procurement.id], body=body, context=context)
            if procurement.sale_line_id and procurement.sale_line_id.order_id:
                procurement.sale_line_id.order_id.message_post(body=body)
