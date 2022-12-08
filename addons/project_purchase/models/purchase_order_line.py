# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            analytic_account_id = False
            if self._context.get('task_id'):
                task = self.env['project.task'].browse(self._context['task_id'])
                analytic_account_id = task.analytic_account_id.id or task.project_id.analytic_account_id.id
            if not analytic_account_id and self._context.get('project_id'):
                analytic_account_id = self.env['project.project'].browse(self._context['project_id']).analytic_account_id.id
            if analytic_account_id:
                line.analytic_distribution = {analytic_account_id: 100}
