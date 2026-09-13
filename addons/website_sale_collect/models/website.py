from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    in_store_dm_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="In-store Delivery Method",
        compute="_compute_in_store_dm_id",
    )

    def _compute_in_store_dm_id(self):
        in_store_delivery_methods = self.env["delivery.carrier"].search(
            [("delivery_type", "=", "in_store"), ("is_published", "=", True)]
        )
        for website in self:
            website.in_store_dm_id = in_store_delivery_methods.filtered_domain(
                [
                    "|",
                    ("website_id", "=", False),
                    ("website_id", "=", website.id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", website.company_id.id),
                ]
            )[:1]

    def _get_product_available_qty(self, product, **kwargs):
        qty_free = super()._get_product_available_qty(product, **kwargs)
        if self.warehouse_id and self.sudo().in_store_dm_id:
            qty_free = max(
                qty_free, self._get_max_in_store_product_available_qty(product)
            )
        return qty_free

    def _get_max_in_store_product_available_qty(self, product):
        return max(
            [
                product.with_context(warehouse_id=wh.id).qty_free
                for wh in self.sudo().in_store_dm_id.warehouse_ids
            ],
            default=0,
        )
