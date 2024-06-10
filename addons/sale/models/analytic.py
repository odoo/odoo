# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.analytic.models import analytic_line, analytic_plan


class AccountAnalyticLine(analytic_line.AccountAnalyticLine):
    so_line = fields.Many2one('sale.order.line', string='Sales Order Item', domain=[('qty_delivered_method', '=', 'analytic')], index='btree_not_null')


class AccountAnalyticApplicability(analytic_plan.AccountAnalyticApplicability):
    business_domain = fields.Selection(
        selection_add=[
            ('sale_order', 'Sale Order'),
        ],
        ondelete={'sale_order': 'cascade'},
    )
