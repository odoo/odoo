# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        if self._context.get('project_id'):
            self.analytic_distribution = {self.env['project.project'].browse(self._context['project_id']).analytic_account_id: 100}
