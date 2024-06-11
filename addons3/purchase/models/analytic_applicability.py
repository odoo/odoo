# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('purchase_order', 'Purchase Order'),
        ],
        ondelete={'purchase_order': 'cascade'},
    )
