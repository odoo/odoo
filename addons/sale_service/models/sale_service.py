# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp import api, models
from openerp.osv import fields, osv
from openerp.exceptions import UserError
from openerp.tools.translate import _


class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'

    def _get_analytic_track_service(self, cr, uid, context=None):
        return super(sale_order_line, self)._get_analytic_track_service(cr, uid, context=context) + ['task']


class procurement_order(osv.osv):
    _name = "procurement.order"
    _inherit = "procurement.order"
    _columns = {
        'task_id': fields.many2one('project.task', 'Task', copy=False),
    }

    def _is_procurement_task(self, cr, uid, procurement, context=None):
        return procurement.product_id.type == 'service' and procurement.product_id.track_service=='task' or False

    def _assign(self, cr, uid, procurement, context=None):
        res = super(procurement_order, self)._assign(cr, uid, procurement, context=context)
        if not res:
            #if there isn't any specific procurement.rule defined for the product, we may want to create a task
            return self._is_procurement_task(cr, uid, procurement, context=context)
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
            if not account:
                procurement.sale_line_id.order_id._create_analytic_account()
                account = procurement.sale_line_id.order_id.project_id
            project_ids = project_project.search(cr, uid, [('analytic_account_id', '=', account.id)])
            projects = project_project.browse(cr, uid, project_ids, context=context)
            project = projects and projects[0]
            if not project:
                project_id = account.project_create({'name': account.name, 'use_tasks': True})
                project = project_project.browse(cr, uid, project_id, context=context)
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


class ProjectTaskStageMrp(osv.Model):
    """ Override project.task.type model to add a 'closed' boolean field allowing
        to know that tasks in this stage are considered as closed. Indeed since
        OpenERP 8.0 status is not present on tasks anymore, only stage_id. """
    _name = 'project.task.type'
    _inherit = 'project.task.type'

    _columns = {
        'closed': fields.boolean('Is a close stage', help="Tasks in this stage are considered as closed."),
    }

    _defaults = {
        'closed': False,
    }


class project_task(osv.osv):
    _name = "project.task"
    _inherit = "project.task"
    _columns = {
        'procurement_id': fields.many2one('procurement.order', 'Procurement', ondelete='set null'),
        'sale_line_id': fields.related('procurement_id', 'sale_line_id', type='many2one', relation='sale.order.line', store=True, string='Sales Order Line'),
    }

    def _validate_subflows(self, cr, uid, ids, context=None):
        proc_obj = self.pool.get("procurement.order")
        for task in self.browse(cr, uid, ids, context=context):
            if task.procurement_id:
                proc_obj.check(cr, SUPERUSER_ID, [task.procurement_id.id], context=context)

    def write(self, cr, uid, ids, values, context=None):
        """ When closing tasks, validate subflows. """
        res = super(project_task, self).write(cr, uid, ids, values, context=context)
        if values.get('stage_id'):
            stage = self.pool.get('project.task.type').browse(cr, uid, values.get('stage_id'), context=context)
            if stage.closed:
                self._validate_subflows(cr, uid, ids, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for task in self.browse(cr, uid, ids, context=context):
            if task.sale_line_id:
                raise UserError(_('You cannot delete a task related to a Sale Order. You can only archive this task.'))
        res = super(project_task, self).unlink(cr, uid, ids, context)
        return res

    def action_view_so(self, cr, uid, ids, context=None):
        task = self.browse(cr, uid, ids, context=context)[0]
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": task.sale_line_id.order_id.id,
            "context": {"create": False, "show_sale": True},
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _need_procurement(self):
        for product in self:
            if product.type == 'service' and product.track_service == 'task':
                return True
        return super(ProductProduct, self)._need_procurement()
