# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    task_id = fields.Many2one('project.task', 'Task', copy=False)

    def _is_procurement_task(self):
        return self.product_id.type == 'service' and self.product_id.track_service == 'task'

    @api.multi
    def _assign(self):
        self.ensure_one()
        res = super(ProcurementOrder, self)._assign()
        if not res:
            # if there isn't any specific procurement.rule defined for the product, we may want to create a task
            return self._is_procurement_task()
        return res

    @api.multi
    def _run(self):
        self.ensure_one()
        if self._is_procurement_task() and not self.task_id:
            # create a task for the procurement
            return self._create_service_task()
        return super(ProcurementOrder, self)._run()

    def _convert_qty_company_hours(self):
        company_time_uom_id = self.env.user.company_id.project_time_mode_id
        if self.product_uom.id != company_time_uom_id.id and self.product_uom.category_id.id == company_time_uom_id.category_id.id:
            planned_hours = self.product_uom._compute_quantity(self.product_qty, company_time_uom_id)
        else:
            planned_hours = self.product_qty
        return planned_hours

    def _get_project(self):
        Project = self.env['project.project']
        project = self.product_id.project_id
        if not project and self.sale_line_id:
            # find the project corresponding to the analytic account of the sales order
            account = self.sale_line_id.order_id.project_id
            if not account:
                self.sale_line_id.order_id._create_analytic_account()
                account = self.sale_line_id.order_id.project_id
            project = Project.search([('analytic_account_id', '=', account.id)], limit=1)
            if not project:
                project_id = account.project_create({'name': account.name, 'use_tasks': True})
                project = Project.browse(project_id)
        return project

    def _create_service_task(self):
        project = self._get_project()
        planned_hours = self._convert_qty_company_hours()
        task = self.env['project.task'].create({
            'name': '%s:%s' % (self.origin or '', self.product_id.name),
            'date_deadline': self.date_planned,
            'planned_hours': planned_hours,
            'remaining_hours': planned_hours,
            'partner_id': self.sale_line_id.order_id.partner_id.id or self.partner_dest_id.id,
            'user_id': self.product_id.product_manager.id,
            'procurement_id': self.id,
            'description': self.name + '\n',
            'project_id': project.id,
            'company_id': self.company_id.id,
        })
        self.write({'task_id': task.id})

        self.message_post(body=_("Task created"))
        if self.sale_line_id.order_id:
            self.sale_line_id.order_id.message_post(body=_("Task created"))

        return task
