# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import analytic


class AccountAnalyticApplicability(analytic.AccountAnalyticApplicability):
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('timesheet', 'Timesheet'),
        ],
        ondelete={'timesheet': 'cascade'},
    )
