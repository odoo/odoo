# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.addons import account


class AccountAnalyticApplicability(account.AccountAnalyticApplicability):
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('purchase_order', 'Purchase Order'),
        ],
        ondelete={'purchase_order': 'cascade'},
    )
