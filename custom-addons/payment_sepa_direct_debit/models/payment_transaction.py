# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    mandate_id = fields.Many2one(comodel_name='sdd.mandate')

    #=== BUSINESS METHODS ===#

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to return SEPA-specific processing values. """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_id.custom_mode != 'sepa_direct_debit' or self.operation == 'online_token':
            return res

        return {
            'access_token': payment_utils.generate_access_token(self.reference),
        }

    def _send_payment_request(self):
        """ Override of payment to create the related `account.payment` and notify the customer.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        :raise: UserError if the transaction is not linked to a valid mandate
        """
        super()._send_payment_request()
        if self.provider_id.custom_mode != 'sepa_direct_debit':
            return

        if not self.token_id:
            raise UserError("SEPA: " + _("The transaction is not linked to a token."))

        mandate = self.token_id.sdd_mandate_id
        if not mandate:
            raise UserError("SEPA: " + _("The token is not linked to a mandate."))

        if (
            mandate.state != 'active'
            or (mandate.end_date and mandate.end_date > fields.Datetime.now())
        ):
            raise UserError("SEPA: " + _("The mandate is invalid."))

        # There is no provider to send a payment request to, but we handle empty notification data
        # to let the payment engine call the generic processing methods.
        self._handle_notification_data('sepa_direct_debit', {'reference': self.reference})

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on dummy data.

        :param str provider_code: The provider_code of the provider that handled the transaction.
        :param dict notification_data: The dummy notification data.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'sepa_direct_debit' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        tx = self.search([
            ('reference', '=', reference),
            ('provider_code', '=', 'custom'),
            ('provider_id.custom_mode', '=', 'sepa_direct_debit'),
        ])
        if not tx:
            raise ValidationError(
                "SEPA: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on dummy data.

        Note: self.ensure_one()

        :param dict notification_data: The dummy notification data.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_id.custom_mode != 'sepa_direct_debit':
            return

        if self.operation in ('online_token', 'offline'):
            self._set_done()  # SEPA transactions are confirmed as soon as the mandate is valid.
            self._sdd_notify_debit(self.token_id)

    def _set_done(self, *args, **kwargs):
        confirmed_txs = super()._set_done(*args, **kwargs)
        sepa_txs = confirmed_txs.filtered(
            lambda t: t.provider_code == 'custom'
                and t.provider_id.custom_mode == 'sepa_direct_debit'
                and t.mandate_id
        )
        for tx in sepa_txs:
            tx.token_id = tx.provider_id._sdd_create_token_for_mandate(tx.partner_id, tx.mandate_id)
            tx.mandate_id._confirm()
        return confirmed_txs

    def _sdd_notify_debit(self, token):
        """ Notify the customer that a debit has been made from his account.

        This is required as per the SEPA Direct Debit rulebook.
        The notice must include:
            - the last 4 digits of the debtor’s bank account
            - the mandate reference
            - the amount to be debited
            - your SEPA creditor identifier
            - your contact information
        Notifications should be sent at least 14 calendar days before the payment is created unless
        specified otherwise.

        :param recordset token: The token linked to the mandate from which the debit has been made,
                                as a `payment.token` record
        :return: None
        """
        ctx = self.env.context.copy()
        ctx.update({
            'iban_last_4': token.payment_details[:4],
            'mandate_ref': token.sdd_mandate_id.name,
            'creditor_identifier': self.env.company.sdd_creditor_identifier,
        })
        template = self.env.ref('payment_sepa_direct_debit.mail_template_sepa_notify_debit')
        template.with_context(ctx).send_mail(self.id)

    def _create_payment(self, **extra_create_values):
        """ Override of `payment` to pass the correct payment method line id and the SDD mandate id
        to the extra create values.

        Note: self.ensure_one()

        :param dict extra_create_values: The optional extra create values.
        :return: The created payment.
        :rtype: recordset of `account.payment`
        """
        if self.provider_id.custom_mode != 'sepa_direct_debit':
            return super()._create_payment(**extra_create_values)

        if self.operation in ('online_token', 'offline'):
            mandate = self.token_id.sdd_mandate_id
        else:
            mandate = self.mandate_id

        payment_method_line = self.provider_id.journal_id.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_provider_id == self.provider_id
        )
        return super()._create_payment(
            payment_method_line_id=payment_method_line.id, sdd_mandate_id=mandate.id
        )
