# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models
from openerp.osv import fields, osv
from openerp.exceptions import UserError
from openerp.tools.translate import _


class procurement_order(osv.osv):
    _name = "procurement.order"
    _inherit = "procurement.order"
    _columns = {
        'task_id': fields.many2one('project.task', 'Task', copy=False),
    }

    def _is_procurement_task(self, cr, uid, ids, context=None):
        procurement = self.browse(cr, uid, ids[0], context=context)
        return procurement.product_id.type == 'service' and procurement.product_id.track_service=='task' or False

    def _assign(self, cr, uid, ids, context=None):
        procurement = self.browse(cr, uid, ids[0], context=context)
        res = super(procurement_order, self)._assign(cr, uid, ids, context=context)
        if not res:
            #if there isn't any specific procurement.rule defined for the product, we may want to create a task
            return procurement._is_procurement_task()
        return res

    def _run(self, cr, uid, ids, context=None):
        procurement = self.browse(cr, uid, ids[0], context=context)
        if procurement._is_procurement_task() and not procurement.task_id:
            # If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a new
            # task.
            if procurement.sale_line_id:
                existing_task = self.pool['project.task'].search(
                    cr, uid, [('sale_line_id', '=', procurement.sale_line_id.id)],
                    context=context
                )
                if existing_task:
                    return existing_task

            #create a task for the procurement
            return self._create_service_task(cr, uid, procurement, context=context)
        return super(procurement_order, self)._run(cr, uid, ids, context=context)

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
            'description': procurement.name + '<br/>',
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


class project_task(osv.osv):
    _name = "project.task"
    _inherit = "project.task"
    _columns = {
        'procurement_id': fields.many2one('procurement.order', 'Procurement', ondelete='set null'),
        'sale_line_id': fields.related('procurement_id', 'sale_line_id', type='many2one', relation='sale.order.line', store=True, string='Sales Order Line'),
    }

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

    def onchange_parent_id(self, cr, uid, ids, parent_id, context=None):
        if not parent_id:
            return {'value' : {'procurement_id': False, 'sale_line_id': False }}
        parent_task = self.browse(cr, uid, parent_id, context=context)
        return {
            'value' : {
                'procurement_id' : parent_task.procurement_id.id,
                'sale_line_id' : parent_task.sale_line_id.id,
            }
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _need_procurement(self):
        for product in self:
            if product.type == 'service' and product.track_service == 'task':
                return True
        return super(ProductProduct, self)._need_procurement()
