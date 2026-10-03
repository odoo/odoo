# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_repr
from odoo.tools.urls import urljoin

QRPH_PRODUCTION_URL = 'https://pg.paymaya.com'
QRPH_SANDBOX_URL = 'https://pg-sandbox.paymaya.com'
QRPH_TIMEOUT = 30


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ph_qrph_public_key = fields.Char(
        string="QRPH Public Key",
        groups='base.group_system',
        help="Public API key of the Maya Business account generating the QRPH codes of this bank account.",
    )
    l10n_ph_qrph_test_mode = fields.Boolean(
        string="QRPH Test Mode",
        default=True,
        help="Generate the QRPH codes on the Maya sandbox. No money is ever moved in this mode.",
    )

    @api.model
    def _get_available_qr_methods(self):
        # EXTENDS account
        rslt = super()._get_available_qr_methods()
        rslt.append(('ph_qrph', self.env._("QRPH"), 40))
        return rslt

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        # EXTENDS account
        if qr_method == 'ph_qrph':
            if not self:
                return self.env._("A bank account is required to generate a QRPH code.")
            if self.country_code != 'PH':
                return self.env._("Can't generate a QRPH code with a bank account that is not in the Philippines.")
            if currency.name != 'PHP':
                return self.env._("Can't generate a QRPH code with a currency other than PHP.")
            if not self.sudo().l10n_ph_qrph_public_key:
                return self.env._(
                    "Please set the QRPH public key on the bank account %(account)s to generate QRPH codes.",
                    account=self.display_name,
                )
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'ph_qrph' and (not amount or amount <= 0):
            # Maya only mints a code for an amount it can charge, so there is no amount-less QRPH code.
            return self.env._("The amount must be set to generate a QRPH code.")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'ph_qrph':
            return self._l10n_ph_qrph_get_qr_code_body(amount, currency, free_communication, structured_communication)

        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'ph_qrph':
            # Asking Maya for a code registers a payment on their side, so it may only happen in front
            # of a customer who is about to pay: never while rendering a PDF or computing a field.
            if not self.env.context.get('is_online_qr'):
                return {}
            return {
                'barcode_type': 'QR',
                'quiet': 0,
                'width': 128,
                'height': 128,
                'value': self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication),
            }

        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _l10n_ph_qrph_get_qr_code_body(self, amount, currency, free_communication, structured_communication):
        """ Return the payload of a QRPH code for the record being paid, asking Maya for a new one if needed.

        The record is taken from the context, as the caller may be paying something that is not
        stored yet, such as an order still being keyed in at the point of sale.

        :param float amount: the amount the code must be paid with
        :param currency: the <res.currency> the amount is expressed in
        :param str free_communication: the free communication of the payment, used as Maya reference
        :param str structured_communication: the structured communication, preferred as Maya reference
        :return: the QR code payload to display to the customer
        :rtype: str
        """
        self.ensure_one()
        model = self.env.context.get('l10n_ph_qrph_model')
        model_id = self.env.context.get('l10n_ph_qrph_model_id')
        QrphTransaction = self.env['l10n_ph.qrph.transaction']

        # Refreshing the payment screen must not pile up payments on Maya's side.
        transaction = QrphTransaction._get_latest_transaction(model, model_id)
        if transaction and transaction._is_reusable(amount):
            return transaction.qr_code_body

        reference = (structured_communication or free_communication or '')[:36] or str(uuid.uuid4())
        response = self._l10n_ph_qrph_make_request('payments/v1/qr/payments', payload={
            'totalAmount': {
                'currency': currency.name,
                'value': float_repr(currency.round(amount), currency.decimal_places),
            },
            'requestReferenceNumber': reference,
        })

        if model and model_id:
            transaction = QrphTransaction.create({
                'model': model,
                'model_id': model_id,
                'bank_id': self.id,
                'currency_id': currency.id,
                'amount': amount,
                'reference': reference,
                'maya_payment_id': response['paymentId'],
                'qr_code_body': response['qrCodeBody'],
            })
            # The link is bookkeeping the payer has no say in, and the field is reserved to accountants.
            if record := transaction._get_record():
                record.sudo().l10n_ph_qrph_transaction_ids |= transaction

        return response['qrCodeBody']

    def _l10n_ph_qrph_fetch_payment_status(self, maya_payment_id):
        """ Return the status Maya reports for one of its payments, e.g. ``PAYMENT_SUCCESS``.

        :param str maya_payment_id: the identifier Maya gave the payment when the code was created
        :rtype: str
        """
        self.ensure_one()
        response = self._l10n_ph_qrph_make_request(f'payments/v1/payments/{maya_payment_id}/status')
        return response.get('status')

    def _l10n_ph_qrph_make_request(self, endpoint, payload=None):
        """ Call the Maya Business API with the credentials of this bank account.

        :param str endpoint: the path to call, relative to the Maya environment of this account
        :param dict payload: the JSON body to post; the request is a GET when there is none
        :return: the decoded JSON answer
        :rtype: dict
        """
        self.ensure_one()
        # Only system users may see the key, but the codes are generated for portal customers and cashiers.
        # It is Maya's publishable key: it can request a payment, never move money out of the account.
        public_key = self.sudo().l10n_ph_qrph_public_key
        base_url = QRPH_SANDBOX_URL if self.l10n_ph_qrph_test_mode else QRPH_PRODUCTION_URL
        try:
            response = requests.request(
                'POST' if payload else 'GET',
                urljoin(base_url, endpoint),
                json=payload,
                auth=(public_key, ''),
                timeout=QRPH_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            raise ValidationError(self.env._("Maya refused the QRPH request: %s", error.response.text))
        except (requests.exceptions.RequestException, ValueError):
            raise ValidationError(self.env._("Could not establish a connection to the Maya API."))
