from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    margin = fields.Float()

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res["margin"] = f"""SUM(l.margin
            / {self._case_value_or_one("o.currency_rate")}
            * {self._case_value_or_one("account_currency_table.rate")})
        """
        return res
