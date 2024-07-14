# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_best_subscription_pricing_rule(self, **kwargs):
        """ Return the best pricing rule for the given duration.
        :param float duration: duration, in unit uom
        :param str unit: duration unit (hour, day, week)
        :param datetime start_date:
        :param datetime end_date:
        :return: least expensive pricing rule for given duration
        """
        self.ensure_one()

        duration, unit = kwargs.get('duration', False), kwargs.get('unit', '')

        if not self.recurring_invoice or not duration or not unit:
            return self.env['sale.subscription.pricing']

        # TODO we might want to change the behaviour
        # For subscription products, we select either the list_price if no pricing correspond to the
        # SO plan_id or the best suited, we don't calculate the lowest price.
        pricelist = kwargs.get('pricelist', self.env['product.pricelist'])
        available_pricings = self.product_subscription_pricing_ids.filtered(lambda p: p.plan_id.billing_period_value == duration and p.plan_id.billing_period_unit == unit and p._applies_to(self))
        best_pricing_with_pricelist = self.env['sale.subscription.pricing']
        best_pricing_without_pricelist = self.env['sale.subscription.pricing']
        for pricing in available_pricings:
            # If there are any variants for the pricing, check if current product id is included in the variants ids.
            variants_ids = pricing.product_variant_ids.ids
            variant_pricing_compatibility = len(variants_ids) == 0 or len(variants_ids) > 0 and self.id in variants_ids
            if pricing.pricelist_id == pricelist and variant_pricing_compatibility:
                best_pricing_with_pricelist |= pricing
            elif not pricing.pricelist_id and variant_pricing_compatibility:
                best_pricing_without_pricelist |= pricing

        return best_pricing_with_pricelist[:1] or best_pricing_without_pricelist[:1] or self.env['sale.subscription.pricing']
