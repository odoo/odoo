from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

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
            company.gateway_ml_spend_this_month = company._gateway_ml_spend_this_month()

    def _gateway_ml_spend_this_month(self):
        self.check_singleton()
        month_start = fields.Datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        [[spent]] = (
            self.env["integration.exchange"]
            .sudo()
            ._read_group(
                [
                    ("company_id", "=", self.id),
                    ("timestamp", ">=", month_start),
                    ("ml_cost", "!=", 0),
                ],
                aggregates=["ml_cost:sum"],
            )
        )
        return spent or 0.0
