# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # link with the sale order
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')

    @api.model
    def form_feedback(self, data, acquirer_name):
        """ Override to confirm the sale order, if defined, and if the transaction
        is done. """
        tx = None
        res = super(PaymentTransaction, self).form_feedback(data, acquirer_name)

        # fetch the tx, check its state, confirm the potential SO
        try:
            tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
            if hasattr(self, tx_find_method_name):
                tx = getattr(self, tx_find_method_name)(data)
            if tx and tx.state == 'done' and tx.acquirer_id.auto_confirm == 'at_pay_confirm' and tx.sale_order_id.state in ['draft', 'sent']:
                tx.sale_order_id.with_context(send_email=True).action_confirm()
            elif tx and tx.state not in ['cancel', 'error'] and tx.sale_order_id.state in ['draft']:
                tx.sale_order_id.force_quotation_send()
        except Exception:
            _logger.exception('Fail to confirm the order or send the confirmation email%s', tx and ' for the transaction %s' % tx.reference or '')

        return res
