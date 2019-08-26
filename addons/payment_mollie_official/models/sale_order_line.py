# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.addons.payment_mollie_official.models.payment_acquirer_method import get_base_url, get_mollie_provider_key

import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('price_unit', 'product_id')
    def _get_price_unit_tax(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit
            taxes = line.tax_id.compute_all(
                price,
                line.order_id.currency_id,
                1,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id)
            line.update({
                'price_unit_taxinc': taxes['total_included'],
            })

    price_unit_taxinc = fields.Float(
        compute='_get_price_unit_tax',
        string='Price Unit Tax inc',
        readonly=True, store=True)
    acquirer_reference = fields.Char(
        string='Acquirer Reference',
        readonly=True,
        help='Reference of the line as stored in the acquirer database')

    @api.model
    def _get_mollie_order_line_data(self, order):
        lines = []
        base_url = get_base_url(self.env)
        for line in order.order_line:
            vatRate = 0.0
            for t in line.tax_id:
                if t.amount_type == 'percent':
                    vatRate += t.amount
            discountAmount = (
                line.price_unit_taxinc - line.price_reduce_taxinc
            ) * int(line.product_uom_qty)
            line_data = {
                'type': "physical",
                'name': line.name,
                'quantity': int(line.product_uom_qty),
                'unitPrice': {
                    "currency": line.currency_id.name,
                    "value": '%.2f' % float(line.price_unit_taxinc)},
                'discountAmount': {
                    "currency": line.currency_id.name,
                    "value": '%.2f' % float(discountAmount)},
                'totalAmount': {
                    "currency": line.currency_id.name,
                    "value": '%.2f' % float(line.price_total)},
                'vatRate': '%.2f' % float(vatRate),
                'vatAmount': {
                    "currency": line.currency_id.name,
                    "value": '%.2f' % float(line.price_tax)},
                'productUrl': '%s/line/%s' % (base_url, line.id),
            }
            lines.append(line_data)
        return lines

    @api.model
    def _set_lines_mollie_ref(self, order_id, response):
        if not response.get('lines', False):
            _logger.info("Error! There was no line found in the response.")
            return False

        for line in response['lines']:
            if not line.get('_links', False):
                _logger.info("Error! No line links found.")
            if not line['_links'].get('productUrl', False):
                _logger.info("Error!_ No line links found in the productUrl.")

            productUrl_dic = line['_links']['productUrl']
            productUrl = productUrl_dic.get("href", "")
            splits = productUrl.split("/")
            line_id = int(splits[-1]) or False
            if not isinstance(line_id, int):
                _logger.info("Error! The lind_id is not an integer_")
                continue
            order_line = self.search([
                ('order_id', '=', order_id),
                ('id', '=', line_id),
            ])
            if len(order_line) == 1:
                order_line.acquirer_reference = line.get('id', '')
            else:
                _logger.info("Error! Multiple sale order lines with the same ID where found.")
                continue
        return True
