# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    referrer_id = fields.Many2one("res.partner", "Referrer", readonly=True)
    commission_plan_id = fields.Many2one("commission.plan", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res["referrer_id"] = "s.referrer_id"
        res["commission_plan_id"] = "s.commission_plan_id"
        return res

    def _group_by_sale(self):
        group_by_str = super()._group_by_sale()
        return f"""{group_by_str},
                    s.referrer_id,
                    s.commission_plan_id
        """
