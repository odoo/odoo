# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, _
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def render_invoice_button(self, invoice):
        values = {
            'partner_id': invoice.partner_id.id,
        }
        return self.acquirer_id.sudo()._render_redirect_form(
            self.reference,
            invoice.amount_residual,
            invoice.currency_id.id,
            **values,
        )
