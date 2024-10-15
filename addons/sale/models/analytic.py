# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account


class AccountAnalyticLine(account.AccountAnalyticLine):

    so_line = fields.Many2one('sale.order.line', string='Sales Order Item', domain=[('qty_delivered_method', '=', 'analytic')], index='btree_not_null')


class AccountAnalyticApplicability(account.AccountAnalyticApplicability):
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('sale_order', 'Sale Order'),
        ],
        ondelete={'sale_order': 'cascade'},
    )
