# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # --------------------------------------------------
    # Sale management
    # --------------------------------------------------

    def _confirm_so(self):
        """ Check tx state, confirm the potential SO"""
        result = super(PaymentTransaction, self)._confirm_so()
        configParameter = self.env['ir.config_parameter'].sudo()
        # check automatic invoice is checked into the ecommerce setting
        if self.state == 'done' and configParameter.get_param('website_sale.automatic_invoice', default=False):
            _logger.info('<%s> transaction completed, auto-confirming order %s (ID %s) and generating invoice', self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
            # Generate the invoice automatically when the order is confirmed
            self._generate_and_pay_invoice()
        return result
