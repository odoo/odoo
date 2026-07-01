# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")

    def write(self, vals):
        websites_to_sync = self.env["website"]
        if "warehouse_id" in vals:
            websites_to_sync = self.filtered("website_sale_unpublish_out_of_stock")
        res = super().write(vals)
        for website in websites_to_sync:
            products_to_check = (
                self
                .env["product.template"]
                .sudo()
                .search([
                    "|",
                    ("is_published", "=", True),
                    ("auto_unpublished_date", "!=", False),
                    "|",
                    ("website_id", "=", website.id),
                    ("website_id", "=", False),
                ])
            )
            products_to_check._sync_website_published_state()
        return res

    def _get_product_available_qty(self, product, **_kwargs):
        """Override of _get_product_available_qty in website_sale module
        Give the available quantity of a given product.

        :param product: product.product record
        :param dict kwargs: unused parameters, available for overrides
        :return: available quantity
        :rtype: float
        """
        return product.with_context(warehouse_id=self.warehouse_id.id).free_qty
