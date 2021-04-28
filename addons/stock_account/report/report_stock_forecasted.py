# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.float_utils import float_is_zero, float_repr


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    def _compute_draft_quantity_count(self, product_template_ids, product_variant_ids, wh_location_ids):
        """ Overrides to computes the valuations of the stock. """
        res = super()._compute_draft_quantity_count(product_template_ids, product_variant_ids, wh_location_ids)
        domain = self._product_domain(product_template_ids, product_variant_ids)
        company = self.env['stock.location'].browse(wh_location_ids).mapped('company_id')
        svl = self.env['stock.valuation.layer'].search(domain + [('company_id', '=', company.id)])
        currency = svl.currency_id or self.env.company.currency_id
        total_quantity = sum(svl.mapped('quantity'))
        # Because we can have negative quantities, `total_quantity` may be equal to zero even if the warehouse's `quantity` is positive.
        if svl and not float_is_zero(total_quantity, precision_rounding=svl.product_id.uom_id.rounding):
            def filter_on_locations(layer):
                return layer.stock_move_id.location_dest_id.id in wh_location_ids or layer.stock_move_id.location_id.id in wh_location_ids
            quantity = sum(svl.filtered(filter_on_locations).mapped('quantity'))
            value = sum(svl.mapped('value')) * (quantity / total_quantity)
        else:
            value = 0
        value = float_repr(value, precision_digits=currency.decimal_places)
        if currency.position == 'after':
            value = '%s %s' % (value, currency.symbol)
        else:
            value = '%s %s' % (currency.symbol, value)
        res['value'] = value
        return res
