from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.stock_landed_costs.models.stock_landed_cost import SPLIT_METHOD


class ProductTemplate(models.Model):
    _inherit = "product.template"

    landed_cost_ok = fields.Boolean(
        string="Is a Landed Cost",
        help="Indicates whether the product is a landed cost: when receiving a vendor bill, you can allocate this cost on preceding receipts.",
    )
    split_method_landed_cost = fields.Selection(
        selection=SPLIT_METHOD,
        string="Default Split Method",
        help="Default Split Method when used for Landed Cost",
    )

    def write(self, vals):
        forced_off = self.browse()
        for product in self:
            if (
                (
                    ("type" in vals and vals["type"] != "service")
                    or ("landed_cost_ok" in vals and not vals["landed_cost_ok"])
                )
                and product.type == "service"
                and product.landed_cost_ok
            ):
                if self.env["account.move.line"].search_count(  # noqa: E8507 - one probe per product losing its landed-cost flag
                    [
                        ("product_id", "in", product.product_variant_ids.ids),
                        ("is_landed_costs_line", "=", True),
                    ],
                    limit=1,
                ):
                    raise UserError(
                        _(
                            "You cannot change the product type or disable landed cost option because the product is used in an account move line."
                        )
                    )
                forced_off |= product

        if forced_off:
            super(ProductTemplate, forced_off).write({**vals, "landed_cost_ok": False})
            remaining = self - forced_off
            return remaining.write(vals) if remaining else True

        return super().write(vals)
