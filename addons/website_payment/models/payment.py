# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, fields, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _name = 'payment.acquirer'
    _inherit = ['payment.acquirer','website.published.mixin']


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
            _logger.info('<%s> transaction processed: tx ref:%s, tx amount: %s', acquirer_name, tx.reference if tx else 'n/a', tx.amount if tx else 'n/a')

            if tx and tx.sale_order_id and tx.sale_order_id.state in ['draft', 'sent']:
                # verify SO/TX match, excluding tx.fees which are currently not included in SO
                amount_matches = float_compare(tx.amount, tx.sale_order_id.amount_total, 2) == 0
                if amount_matches:
                    if tx.state == 'done' and tx.acquirer_id.auto_confirm == 'at_pay_confirm':
                        _logger.info('<%s> transaction completed, auto-confirming order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
                        tx.sale_order_id.with_context(send_email=True).action_confirm()
                    elif tx.state not in ['cancel', 'error'] and tx.sale_order_id.state == 'draft':
                        _logger.info('<%s> transaction pending/to confirm manually, sending quote email for order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
                        tx.sale_order_id.force_quotation_send()
                else:
                    _logger.warning('<%s> transaction MISMATCH for order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
        except Exception:
            _logger.exception('Fail to confirm the order or send the confirmation email%s', tx and ' for the transaction %s' % tx.reference or '')

        return res
