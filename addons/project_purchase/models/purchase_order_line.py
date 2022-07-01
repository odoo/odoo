# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _default_account_analytic_id(self):
        if self._context.get('project_id'):
            return self.env['project.project'].browse(self._context['project_id']).analytic_account_id
        return False

    account_analytic_id = fields.Many2one(default=_default_account_analytic_id)
