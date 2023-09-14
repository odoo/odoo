# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    allowed_so_line_ids = fields.Many2many('sale.order.line', compute='_compute_allowed_so_line_ids')
    so_line = fields.Many2one('sale.order.line', string='Sales Order Item', domain="[('id', 'in', allowed_so_line_ids)]")

    def _default_sale_line_domain(self):
        """ This is only used for delivered quantity of SO line based on analytic line, and timesheet
            (see sale_timesheet). This can be override to allow further customization.
        """
        self.ensure_one()
        return [('qty_delivered_method', '=', 'analytic')]

    def _compute_allowed_so_line_ids(self):
        for timesheet in self:
            domain = timesheet._default_sale_line_domain()
            timesheet.allowed_so_line_ids = self.env['sale.order.line'].search(domain)


class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('sale_order', 'Sale Order'),
        ],
        ondelete={'sale_order': 'cascade'},
    )
