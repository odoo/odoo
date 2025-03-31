# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    in_store_dm_id = fields.Many2one(
        string="In-store Delivery Method",
        comodel_name='delivery.carrier',
        compute='_compute_in_store_dm_id',
    )

    def _compute_in_store_dm_id(self):
        in_store_delivery_methods = self.env['delivery.carrier'].search(
            [('delivery_type', '=', 'in_store'), ('is_published', '=', True)]
        )
        for website in self:
            website.in_store_dm_id = in_store_delivery_methods.filtered_domain([
               '|', ('website_id', '=', False), ('website_id', '=', website.id),
               '|', ('company_id', '=', False), ('company_id', '=', website.company_id.id),
            ])[:1]

    def _get_product_available_qty(self, product, **kwargs):
        """ Override of `website_sale_stock` to include free quantities of the product in warehouses
         of in-store delivery method and return maximum possible for one order. Needed only if a
         warehouse is set on website, otherwise free quantity is already calculated from all
         warehouses."""
        free_qty = super()._get_product_available_qty(product, **kwargs)
        if self.warehouse_id and self.sudo().in_store_dm_id:  # If warehouse is set on website.
            # Check free quantities in the in-store warehouses.
            free_qty = max(free_qty, self._get_max_in_store_product_available_qty(product))
        return free_qty

    def _get_max_in_store_product_available_qty(self, product):
        """ Return maximum amount of product available to deliver with in store delivery method. """
        return max([
            product.with_context(warehouse_id=wh.id).free_qty
            for wh in self.sudo().in_store_dm_id.warehouse_ids
        ], default=0)
