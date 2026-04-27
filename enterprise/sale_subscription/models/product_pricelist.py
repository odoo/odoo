# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    product_subscription_pricing_ids = fields.One2many(
        'sale.subscription.pricing',
        'pricelist_id',
        string="Recurring Pricing",
        domain=[
            '|', ('product_template_id', '=', None), ('product_template_id.active', '=', True),
        ],
        copy=True,
    )

    def toggle_active(self):
        """
        Archiving and unArchiving the price list and its product subscription pricing.
        1. When archiving
        We want to be archiving the product subscription pricing FIRST.
        The record of product_subscription_pricing_ids will be inactive when the price-list is archived.

        2. When un-archiving
        We want to un-archive the product subscription pricing LAST.
        The record of the product_subscription_pricing_ids will be active when the price list is unarchived."""
        self.with_context({'active_test': False}).product_subscription_pricing_ids.toggle_active()
        return super().toggle_active()
