# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.partner_shipping_id.country_id.intrastat:
            res['intrastat_country_id'] = self.partner_shipping_id.country_id.id
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        invoice_line = super()._prepare_invoice_line(**optional_values)
        invoice_line['intrastat_product_origin_country_id'] = self.product_id.intrastat_origin_country_id.id
        return invoice_line
