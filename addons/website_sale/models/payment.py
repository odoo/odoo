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
        """Generate the invoice automatically when option is enabled from ecommerce setting"""
        result = super(PaymentTransaction, self)._confirm_so()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        if self.state == 'done' and IrConfigParameter.get_param('website_sale.automatic_invoice', default=False):
            _logger.info('<%s> transaction completed, generating invoice for order %s (ID %s)', self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
            self._generate_and_pay_invoice()
        return result
