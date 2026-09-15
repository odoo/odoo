from odoo import models


class LoyaltyReward(models.Model):
    _inherit = "loyalty.reward"

    def _prepare_discount_product_vals(self):
        res = super()._prepare_discount_product_vals()
        for vals in res:
            vals.update(
                {
                    "taxes_id": False,
                    "supplier_taxes_id": False,
                    "invoice_policy": "ordered",
                }
            )
        return res

    def unlink(self):
        if len(self) == 1 and self.env["sale.order.line"].sudo().search_count(
            [("reward_id", "in", self.ids)], limit=1
        ):
            return self.action_archive()
        return super().unlink()
