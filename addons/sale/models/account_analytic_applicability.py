from odoo import fields, models


class AccountAnalyticApplicability(models.Model):
    _inherit = "account.analytic.applicability"
    _description = "Analytic Plan's Applicabilities"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    business_domain = fields.Selection(
        selection_add=[
            ("sale_order", "Sale Order"),
        ],
        ondelete={"sale_order": "cascade"},
    )
