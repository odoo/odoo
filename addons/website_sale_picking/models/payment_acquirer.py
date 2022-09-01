# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    custom_mode = fields.Selection(
        selection_add=[('onsite', "On Site")]
    )

    @api.model
    def _get_compatible_acquirers(self, *args, sale_order_id=None, website_id=None, **kwargs):
        """ Override of payment to exclude onsite acquirers if the delivery doesn't match.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :param int website_id: The provided website, as a `website` id
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        compatible_acquirers = super()._get_compatible_acquirers(
            *args, sale_order_id=sale_order_id, website_id=website_id, **kwargs)
        # Show on site picking only if delivery carriers onsite exists
        onsite_carriers = self.env['delivery.carrier'].search([
            ('website_published', '=', True),
            ('delivery_type', '=', 'onsite'),
            '|',
                ('website_id', '=?', website_id),
                ('website_id', '=', False)
        ])
        order = self.env['sale.order'].browse(sale_order_id).exists()

        # Show onsite acquirers only if onsite carriers exists
        # and the order contains physical products
        if not onsite_carriers or not any(
            product.type in ('consu', 'product')
            for product in order.order_line.product_id
        ):
            compatible_acquirers.filtered(
                lambda acq: acq.provider != 'custom' or acq.custom_mode != 'onsite'
            )

        return compatible_acquirers
