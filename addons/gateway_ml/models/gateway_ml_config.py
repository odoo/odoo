from odoo import fields, models


class GatewayMlConfig(models.Model):
    _name = "gateway_ml.config"
    _description = "A company's gateway ml configuration"
    _inherit = ["mixin.company.config"]

    gateway_ml_monthly_budget = fields.Float(
        string="Monthly ML Budget (USD)",
        groups="base.group_system",
        help="Once this company's machine learning exchanges of the current month "
        "have cost this much at the model rows' prices, no further call to a "
        "machine learning vendor is made until the month turns. Zero sets no cap.",
    )
    gateway_ml_spend_this_month = fields.Float(
        string="ML Spend This Month (USD)",
        compute="_compute_gateway_ml_spend_this_month",
        groups="base.group_system",
        help="What this company's machine learning exchanges since the first of "
        "the month cost, as recorded on their exchange rows.",
    )

    def _compute_gateway_ml_spend_this_month(self):
        for company in self:
            company.gateway_ml_spend_this_month = (
                company.company_id._gateway_ml_spend_this_month()
            )
