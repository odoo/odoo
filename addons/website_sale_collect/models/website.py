# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.http import request

CLICK_AND_COLLECT_SESSION_CACHE_KEY = "website_sale_collect_pending_selection"


class Website(models.Model):
    _inherit = "website"

    in_store_dm_id = fields.Many2one(
        string="In-store Delivery Method",
        comodel_name="delivery.carrier",
        compute="_compute_in_store_dm_id",
    )

    def _create_cart(self):
        """Override to apply the Click & Collect selection made on the product page, if any, before
        this cart existed."""
        sale_order_sudo = super()._create_cart()
        pending_selection = request.session.pop(CLICK_AND_COLLECT_SESSION_CACHE_KEY, None)
        if pending_selection:
            sale_order_sudo._apply_pending_cac_selection(pending_selection)
        return sale_order_sudo

    def _compute_in_store_dm_id(self):
        in_store_delivery_methods = self.env["delivery.carrier"].search([
            ("delivery_type", "=", "in_store"),
            ("is_published", "=", True),
        ])
        for website in self:
            website.in_store_dm_id = in_store_delivery_methods.filtered_domain([
                "|",
                ("website_id", "=", False),
                ("website_id", "=", website.id),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", website.company_id.id),
            ])[:1]

    def _get_product_available_qty(self, product, **kwargs):
        """Override of `website_sale_stock` to include free quantities of the product in warehouses
        of in-store delivery method.

        If Click and Collect is enabled, and a warehouse is set on the website, return the maximum
        between the website's warehouse stock and the best stock available among all in-store
        warehouses.
        """
        free_qty = super()._get_product_available_qty(product, **kwargs)
        # As we can have warehouses from other companies in the available pick up stores, in such case we always need
        # to take the pick up store quantity into account, as they won't be factored in the company-specific free_qty.
        if self.sudo().in_store_dm_id and (
            self.warehouse_id
            or any(
                w.company_id != self.company_id for w in self.sudo().in_store_dm_id.warehouse_ids
            )
        ):
            # Check free quantities in the in-store warehouses.
            return max(free_qty, self._get_max_in_store_product_available_qty(product, **kwargs))
        return free_qty

    def _get_max_in_store_product_available_qty(self, product, **kwargs):
        """Return the maximum amount of product available to deliver with in store dm."""
        return max(
            (
                super(Website, self)._get_product_available_qty(
                    product, warehouse_id=wh.id, **kwargs
                )
                for wh in self.sudo().in_store_dm_id.warehouse_ids
            ),
            default=0,
        )
