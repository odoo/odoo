# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.float_utils import float_is_zero, float_repr


class StockForecasted(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        """ Overrides to computes the valuations of the stock. """
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        if not self.user_has_groups('stock.group_stock_manager') or not wh_location_ids:
            return res
        domain = self._product_domain(product_template_ids, product_ids)
        company = self.env['stock.location'].browse(wh_location_ids[0]).company_id
        svl = self.env['stock.valuation.layer'].search(domain + [('company_id', '=', company.id)])
        domain_quants = [
            ('company_id', '=', company.id),
            ('location_id', 'in', wh_location_ids)
        ]
        if product_template_ids:
            domain_quants += [('product_id.product_tmpl_id', 'in', product_template_ids)]
        else:
            domain_quants += [('product_id', 'in', product_ids)]
        quants = self.env['stock.quant'].search(domain_quants)
        currency = svl.currency_id or self.env.company.currency_id
        total_quantity = sum(svl.mapped('quantity'))
        # Because we can have negative quantities, `total_quantity` may be equal to zero even if the warehouse's `quantity` is positive.
        if svl and not float_is_zero(total_quantity, precision_rounding=svl.product_id.uom_id.rounding):
            value = sum(svl.mapped('value')) * (sum(quants.mapped('quantity')) / total_quantity)
        else:
            value = 0
        value = float_repr(value, precision_digits=currency.decimal_places)
        if currency.position == 'after':
            value = '%s %s' % (value, currency.symbol)
        else:
            value = '%s %s' % (currency.symbol, value)
        res['value'] = value
        return res
