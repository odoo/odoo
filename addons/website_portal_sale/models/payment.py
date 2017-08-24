# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, fields, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # link with the sale order
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')

    def _generate_and_pay_invoice(self, tx, acquirer_name):
        tx.sale_order_id._force_lines_to_invoice_policy_order()

        # force company to ensure journals/accounts etc. are correct
        # company_id needed for default_get on account.journal
        # force_company needed for company_dependent fields
        ctx_company = {'company_id': tx.sale_order_id.company_id.id,
                       'force_company': tx.sale_order_id.company_id.id}
        created_invoice = tx.sale_order_id.with_context(**ctx_company).action_invoice_create()
        created_invoice = self.env['account.invoice'].browse(created_invoice).with_context(**ctx_company)

        if created_invoice:
            _logger.info('<%s> transaction completed, auto-generated invoice %s (ID %s) for %s (ID %s)',
                         acquirer_name, created_invoice.name, created_invoice.id, tx.sale_order_id.name, tx.sale_order_id.id)

            created_invoice.action_invoice_open()
            if tx.acquirer_id.journal_id:
                created_invoice.pay_and_reconcile(tx.acquirer_id.journal_id, pay_amount=created_invoice.amount_total)
                if created_invoice.payment_ids:
                    created_invoice.payment_ids[0].payment_transaction_id = tx
            else:
                _logger.warning('<%s> transaction completed, could not auto-generate payment for %s (ID %s) (no journal set on acquirer)',
                                acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
        else:
            _logger.warning('<%s> transaction completed, could not auto-generate invoice for %s (ID %s)',
                            acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)

    @api.model
    def form_feedback(self, data, acquirer_name):
        """ Override to confirm the sale order, if defined, and if the transaction
        is done. """
        tx = None
        res = super(PaymentTransaction, self).form_feedback(data, acquirer_name)

        # fetch the tx
        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            tx = getattr(self, tx_find_method_name)(data)
        _logger.info('<%s> transaction processed: tx ref:%s, tx amount: %s', acquirer_name, tx.reference if tx else 'n/a', tx.amount if tx else 'n/a')

        if tx:
            # Auto-confirm SO if necessary
            tx._confirm_so(acquirer_name=acquirer_name)

        return res

    def _confirm_so(self, acquirer_name=False):
        for tx in self:
            # check tx state, confirm the potential SO
            if tx.sale_order_id and tx.sale_order_id.state in ['draft', 'sent']:
                # verify SO/TX match, excluding tx.fees which are currently not included in SO
                amount_matches = float_compare(tx.amount, tx.sale_order_id.amount_total, 2) == 0
                if amount_matches:
                    if not acquirer_name:
                        acquirer_name = tx.acquirer_id.provider or 'unknown'
                    if tx.state == 'authorized' and tx.acquirer_id.auto_confirm == 'authorize':
                        _logger.info('<%s> transaction authorized, auto-confirming order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
                        tx.sale_order_id.with_context(send_email=True).action_confirm()
                    if tx.state == 'done' and tx.acquirer_id.auto_confirm in ['confirm_so', 'generate_and_pay_invoice']:
                        _logger.info('<%s> transaction completed, auto-confirming order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
                        tx.sale_order_id.with_context(send_email=True).action_confirm()

                        if tx.acquirer_id.auto_confirm == 'generate_and_pay_invoice':
                            self._generate_and_pay_invoice(tx, acquirer_name)
                    elif tx.state not in ['cancel', 'error'] and tx.sale_order_id.state == 'draft':
                        _logger.info('<%s> transaction pending/to confirm manually, sending quote email for order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
                        tx.sale_order_id.force_quotation_send()
                else:
                    _logger.warning('<%s> transaction MISMATCH for order %s (ID %s)', acquirer_name, tx.sale_order_id.name, tx.sale_order_id.id)
