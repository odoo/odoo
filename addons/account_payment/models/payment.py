# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, _
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    account_invoice_id = fields.Many2one('account.invoice', string='Invoice')

    def form_feedback(self, data, acquirer_name):
        """ Override to confirm the invoice, if defined, and if the transaction is done. """
        tx = None
        res = super(PaymentTransaction, self).form_feedback(data, acquirer_name)

        # fetch the tx
        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            tx = getattr(self, tx_find_method_name)(data)

        if tx and tx.account_invoice_id:
            _logger.info(
                '<%s> transaction <%s> processing form feedback for invoice <%s>: tx ref:%s, tx amount: %s',
                acquirer_name, tx.id, tx.account_invoice_id.id, tx.reference, tx.amount)
            tx._confirm_invoice()

        return res

    def confirm_invoice_token(self):
        """ Confirm a transaction token and call SO confirmation if it is a success.

        :return: True if success; error string otherwise """
        self.ensure_one()
        if self.payment_token_id and self.partner_id == self.account_invoice_id.partner_id:
            try:
                s2s_result = self.s2s_do_transaction()
            except Exception as e:
                _logger.warning(
                    _("<%s> transaction (%s) failed : <%s>") %
                    (self.acquirer_id.provider, self.id, str(e)))
                return 'pay_invoice_tx_fail'

            valid_state = 'authorized' if self.acquirer_id.capture_manually else 'done'
            if not s2s_result or self.state != valid_state:
                _logger.warning(
                    _("<%s> transaction (%s) invalid state : %s") %
                    (self.acquirer_id.provider, self.id, self.state_mesage))
                return 'pay_invoice_tx_state'

            try:
                # Auto-confirm SO if necessary
                return self._confirm_invoice()
            except Exception as e:
                _logger.warning(
                    _("<%s>  transaction (%s) invoice confirmation failed : <%s>") %
                    (self.acquirer_id.provider, self.id, str(e)))
                return 'pay_invoice_tx_confirm'
        return 'pay_invoice_tx_token'

    def _confirm_invoice(self):
        """ Check tx state, confirm and pay potential invoice """
        self.ensure_one()
        # check tx state, confirm the potential SO
        if self.account_invoice_id.state != 'open':
            _logger.warning('<%s> transaction STATE INCORRECT for invoice %s (ID %s, state %s)', self.acquirer_id.provider, self.account_invoice_id.number, self.account_invoice_id.id, self.account_invoice_id.state)
            return 'pay_invoice_invalid_doc_state'
        if not float_compare(self.amount, self.account_invoice_id.amount_total, 2) == 0:
            _logger.warning(
                '<%s> transaction AMOUNT MISMATCH for invoice %s (ID %s): expected %r, got %r',
                self.acquirer_id.provider, self.account_invoice_id.number, self.account_invoice_id.id,
                self.account_invoice_id.amount_total, self.amount,
            )
            self.account_invoice_id.message_post(
                subject=_("Amount Mismatch (%s)") % self.acquirer_id.provider,
                body=_("The invoice was not confirmed despite response from the acquirer (%s): invoice amount is %r but acquirer replied with %r.") % (
                    self.acquirer_id.provider,
                    self.account_invoice_id.amount_total,
                    self.amount,
                )
            )
            return 'pay_invoice_tx_amount'

        if self.state == 'authorized' and self.acquirer_id.capture_manually:
            _logger.info('<%s> transaction authorized, nothing to do with invoice %s (ID %s)', self.acquirer_id.provider, self.account_invoice_id.number, self.account_invoice_id.id)
        elif self.state == 'done':
            _logger.info('<%s> transaction completed, paying invoice %s (ID %s)', self.acquirer_id.provider, self.account_invoice_id.number, self.account_invoice_id.id)
            self._pay_invoice()
        else:
            _logger.warning('<%s> transaction MISMATCH for invoice %s (ID %s)', self.acquirer_id.provider, self.account_invoice_id.number, self.account_invoice_id.id)
            return 'pay_invoice_tx_state'
        return True

    def _pay_invoice(self):
        self.ensure_one()

        # force company to ensure journals/accounts etc. are correct
        # company_id needed for default_get on account.journal
        # force_company needed for company_dependent fields
        ctx_company = {'company_id': self.account_invoice_id.company_id.id,
                       'force_company': self.account_invoice_id.company_id.id}
        invoice = self.account_invoice_id.with_context(**ctx_company)

        if not self.acquirer_id.journal_id:
            default_journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
            if not default_journal:
                _logger.warning('<%s> transaction completed, could not auto-generate payment for invoice %s (ID %s) (no journal set on acquirer)',
                                self.acquirer_id.provider, self.account_invoice_id.number, self.account_invoice_id.id)
                return False
            self.acquirer_id.journal_id = default_journal

        invoice.pay_and_reconcile(self.acquirer_id.journal_id, pay_amount=invoice.amount_total)
        invoice.payment_ids.write({'payment_transaction_id': self.ids[0]})
        _logger.info('<%s> transaction <%s> completed, reconciled invoice %s (ID %s))',
                     self.acquirer_id.provider, self.ids[0], invoice.number, invoice.id)

        return True

    def render_invoice_button(self, invoice, return_url, submit_txt=None, render_values=None):
        values = {
            'return_url': return_url,
            'partner_id': invoice.partner_id.id,
        }
        if render_values:
            values.update(render_values)
        return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            self.reference,
            invoice.amount_total,
            invoice.currency_id.id,
            values=values,
        )

    def _check_or_create_invoice_tx(self, invoice, acquirer, payment_token=None, tx_type='form', add_tx_values=None):
        tx = self
        if not tx:
            tx = self.search([('reference', '=', invoice.number)], limit=1)

        if tx and tx.state in ['error', 'cancel']:  # filter incorrect states
            tx = False
        if (tx and acquirer and tx.acquirer_id != acquirer) or (tx and tx.account_invoice_id != invoice):  # filter unmatching
            tx = False
        if tx and tx.payment_token_id and payment_token and payment_token != tx.payment_token_id:  # new or distinct token
            tx = False

        # still draft tx, no more info -> create a new one
        if tx and tx.state == 'draft':
            tx = False

        if not tx:
            tx_values = {
                'acquirer_id': acquirer.id,
                'type': tx_type,
                'amount': invoice.amount_total,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'partner_country_id': invoice.partner_id.country_id.id,
                'reference': self._get_next_reference(invoice.number, acquirer=acquirer),
                'account_invoice_id': invoice.id,
            }
            if add_tx_values:
                tx_values.update(add_tx_values)
            if payment_token and payment_token.sudo().partner_id == invoice.partner_id:
                tx_values['payment_token_id'] = payment_token.id

            tx = self.create(tx_values)

        # update invoice
        invoice.write({
            'payment_tx_id': tx.id,
        })

        return tx

    def _post_process_after_done(self, **kwargs):
        # set invoice id in payment transaction when payment being done from sale order
        res = super(PaymentTransaction, self)._post_process_after_done()
        if kwargs.get('invoice_id'):
            self.account_invoice_id = kwargs['invoice_id']
        return res
