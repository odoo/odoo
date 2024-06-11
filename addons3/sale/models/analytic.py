# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    # [XBO] TODO: remove me in master
    allowed_so_line_ids = fields.Many2many('sale.order.line', compute='_compute_allowed_so_line_ids')
    so_line = fields.Many2one('sale.order.line', string='Sales Order Item', domain=[('qty_delivered_method', '=', 'analytic')], index='btree_not_null')

    def _default_sale_line_domain(self):
        """ This is only used for delivered quantity of SO line based on analytic line, and timesheet
            (see sale_timesheet). This can be override to allow further customization.
            [XBO] TODO: remove me in master
        """
        return [('qty_delivered_method', '=', 'analytic')]

    def _compute_allowed_so_line_ids(self):
        # [XBO] TODO: remove me in master
        self.allowed_so_line_ids = False

class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('sale_order', 'Sale Order'),
        ],
        ondelete={'sale_order': 'cascade'},
    )
