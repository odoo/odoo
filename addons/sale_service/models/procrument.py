# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    task_id = fields.Many2one('project.task', string='Task', copy=False)

    @api.multi
    def _is_procurement_task(self):
        self.ensure_one()
        return self.product_id.type == 'service' and self.product_id.auto_create_task or False

    # It is not possible to call v8 method from v7, as we need to pass self while calling super.
    # Eg ProcurementOrder, self)._assign(self).So better to put two version method and removing v7 after procrument module migration

    @api.v7
    def _assign(self, cr, uid, procurement, context=None):
        res = super(ProcurementOrder, self)._assign(cr, uid, procurement, context=context)
        if not res and procurement._is_procurement_task():
            #if there isn't any specific procurement.rule defined for the product, we may want to create a task
            return True
        return res

    @api.v8
    def _assign(self):
        res = super(ProcurementOrder, self)._assign()
        if not res and self._is_procurement_task():
            #if there isn't any specific procurement.rule defined for the product, we may want to create a task
            return True
        return res

    @api.v7
    def _run(self, cr, uid, procurement, context=None):
        if procurement._is_procurement_task() and not procurement.task_id:
            #create a task for the procurement
            return procurement._create_service_task()
        return super(ProcurementOrder, self)._run(cr, uid, procurement, context=context)

    @api.v8
    def _run(self):
        if self._is_procurement_task() and not self.task_id:
            #create a task for the procurement
            return self._create_service_task()
        return super(ProcurementOrder, self)._run()

    @api.v7
    def _check(self, cr, uid, procurement, context=None):
        if procurement._is_procurement_task():
            return procurement.task_id and procurement.task_id.stage_id.closed or False
        return super(ProcurementOrder, self)._check(cr, uid, procurement, context=context)

    @api.v8
    def _check(self):
        if self._is_procurement_task():
            return self.task_id and self.task_id.stage_id.closed or False
        return super(ProcurementOrder, self)._check()

    @api.multi
    def _convert_qty_company_hours(self):
        self.ensure_one()
        company_time_uom = self.env.user.company_id.project_time_mode_id
        if self.product_uom.id != company_time_uom.id and self.product_uom.category_id.id == company_time_uom.category_id.id:
            planned_hours = self.env['product.uom']._compute_qty(self.product_uom.id, self.product_qty, company_time_uom.id)
        else:
            planned_hours = self.product_qty
        return planned_hours

    @api.multi
    def _get_project(self):
        self.ensure_one()
        project = self.product_id.project_id
        if not project and self.sale_line_id:
            # find the project corresponding to the analytic account of the sales order
            account = self.sale_line_id.order_id.project_id
            project = self.env['project.project'].search([('analytic_account_id', '=', account.id)], limit=1)
        return project or False

    @api.one
    def _create_service_task(self):
        project = self._get_project()
        planned_hours = self._convert_qty_company_hours()
        task = self.env['project.task'].create({
            'name': '%s:%s' % (self.origin or '', self.product_id.name),
            'date_deadline': self.date_planned,
            'planned_hours': planned_hours,
            'remaining_hours': planned_hours,
            'partner_id': self.sale_line_id and self.sale_line_id.order_id.partner_id.id or self.partner_dest_id.id,
            'user_id': self.product_id.product_manager.id,
            'procurement_id': self.id,
            'description': self.name + '\n',
            'project_id': project and project.id or False,
            'company_id': self.company_id.id,
        })
        self.task_id = task.id
        self.project_task_create_note()
        return task.id

    @api.multi
    def project_task_create_note(self):
        for procurement in self:
            body = _("Task created")
            self.message_post(body=body)
            if procurement.sale_line_id and procurement.sale_line_id.order_id:
                procurement.sale_line_id.order_id.message_post(body=body)
