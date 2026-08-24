# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import models, fields
from odoo.tools.float_utils import float_repr


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        """ Overrides to computes the valuations of the stock. """
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        if not self.env.user.has_group('stock.group_stock_manager') or not wh_location_ids:
            return res
        locations = self.env['stock.location'].browse(wh_location_ids)
        company = locations.company_id
        domain_quants = [
            ('company_id', 'in', company.ids),
            ('location_id', 'in', wh_location_ids)
        ]
        if product_template_ids:
            domain_quants += [('product_id.product_tmpl_id', 'in', product_template_ids)]
        else:
            domain_quants += [('product_id', 'in', product_ids)]
        quants = self.env['stock.quant'].search(domain_quants)
        warehouses = locations.warehouse_id

        currency = self.env.company.currency_id
        values_per_warehouse = defaultdict(float)
        for quant in quants:
            values_per_warehouse[quant.warehouse_id.id] += quant.value

        def format_value(value, currency):
            value = float_repr(value, precision_digits=currency.decimal_places)
            return (
                f"{value} {currency.symbol}"
                if currency.position == "after"
                else f"{currency.symbol} {value}"
            )
        total_value = 0.0
        res['values_per_warehouse'] = {}

        for warehouse in warehouses:
            value = values_per_warehouse[warehouse.id]
            warehouse_currency = warehouse.company_id.currency_id

            res['values_per_warehouse'][warehouse.id] = format_value(
                value,
                warehouse_currency,
            )

            if warehouse_currency == currency:
                total_value += value
            else:
                total_value += warehouse_currency._convert(
                    value,
                    currency,
                    warehouse.company_id,
                    fields.Date.context_today(self),
                )

                res['total_value'] = format_value(total_value, currency)

        return res
