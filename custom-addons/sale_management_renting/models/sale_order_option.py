# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class SaleOrderOption(models.Model):
    _inherit = 'sale.order.option'

    def add_option_to_order(self):
        """ Override to add the rental context so that new SOL can be flagged as rental """
        if self.order_id.is_rental_order:
            self = self.with_context(in_rental_app=True)
        return super().add_option_to_order()

    def _get_values_to_add_to_order(self):
        """ Override to remove the name and force its recomputation to add the period on the SOL """
        vals = super()._get_values_to_add_to_order()
        if self.order_id.is_rental_order and self.product_id.rent_ok:
            vals.pop('name')
        return vals

    @api.model
    def _product_id_domain(self):
        """ Override to allow users to add a rental product as a sale order option """
        return expression.OR([super()._product_id_domain(), [('rent_ok', '=', True)]])
