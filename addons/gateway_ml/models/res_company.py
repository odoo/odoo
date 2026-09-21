from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    gateway_ml_config_id = fields.Many2one(
        comodel_name="gateway_ml.config",
        compute="_compute_gateway_ml_config_id",
        search="_search_gateway_ml_config_id",
    )

    gateway_ml_monthly_budget = fields.Float(
        related="gateway_ml_config_id.gateway_ml_monthly_budget",
        readonly=False,
    )
    gateway_ml_spend_this_month = fields.Float(
        related="gateway_ml_config_id.gateway_ml_spend_this_month",
    )

    def _search_gateway_ml_config_id(self, operator, value):
        return self._search_config_link("gateway_ml.config", operator, value)

    def _compute_gateway_ml_config_id(self):
        configs = self.env["gateway_ml.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.gateway_ml_config_id = by_company.get(company.id, False)

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
