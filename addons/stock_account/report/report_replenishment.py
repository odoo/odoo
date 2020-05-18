# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.float_utils import float_repr


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    @api.model
    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        """ Overrides to computes the valuations of the stock. """
        res = super()._get_report_data(product_template_ids, product_variant_ids)
        domain = self._product_domain(product_template_ids, product_variant_ids)
        svl = self.env['stock.valuation.layer'].search(domain)
        currency = svl.currency_id or self.env.company.currency_id
        value = float_repr(sum(svl.mapped('value')), precision_digits=currency.decimal_places)
        if currency.position == 'after':
            value = '%s %s' % (value, currency.symbol)
        else:
            value = '%s %s' % (currency.symbol, value)
        res['value'] = value
        return res
