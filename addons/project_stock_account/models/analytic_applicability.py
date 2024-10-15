# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account


class AccountAnalyticApplicability(account.AccountAnalyticApplicability):
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('stock_picking', 'Stock Picking'),
        ],
        ondelete={'stock_picking': 'cascade'},
    )
