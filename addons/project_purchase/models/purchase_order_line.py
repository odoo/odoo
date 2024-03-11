# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if line._context.get('project_id'):
                line.analytic_distribution = {line.env['project.project'].browse(line._context['project_id']).analytic_account_id.id: 100}
