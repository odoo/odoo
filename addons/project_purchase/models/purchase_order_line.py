# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        analytic_account = self.env['account.analytic.account']
        if self._context.get('task_id'):
            task = self.env['project.task'].browse(self._context['task_id'])
            analytic_account = task.analytic_account_id or task.project_id.analytic_account_id
        if not analytic_account and self._context.get('project_id'):
            analytic_account = self.env['project.project'].browse(self._context['project_id']).analytic_account_id
        if analytic_account and analytic_account.active:
            for line in self:
                line.analytic_distribution = {analytic_account.id: 100}
