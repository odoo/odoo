# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_repr
from odoo.tools.urls import urljoin

from odoo.addons.l10n_ph_qrph_maya import const

# The Maya API, as in the Pay with Maya QR documentation.
PRODUCTION_URL = 'https://pg.paymaya.com'
SANDBOX_URL = 'https://pg-sandbox.paymaya.com'
CREATE_PAYMENT_ENDPOINT = 'payments/v1/qr/payments'
PAYMENT_STATUS_ENDPOINT = 'payments/v1/payments/{payment_id}/status'
REQUEST_TIMEOUT = 30


class MayaRequestError(ValidationError):
    """ Maya refused a request, or could not be reached. """


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ph_qrph_public_key = fields.Char(
        string="QRPH Public Key",
        groups='base.group_system',
        copy=False,
        help="Public API key of the Maya Business account generating the QRPH codes of this bank account.",
    )
    l10n_ph_qrph_test_mode = fields.Boolean(
        string="QRPH Test Mode",
        groups='base.group_system',
        default=True,
        copy=False,
        help="Generate the QRPH codes on the Maya sandbox. No money is ever moved in this mode.",
    )

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append((const.QR_METHOD, self.env._("QRPH (Maya)"), 40))
        return rslt

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == const.QR_METHOD:
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
        if qr_method == const.QR_METHOD and (not amount or amount <= 0):
            # Maya only mints a code for an amount it can charge, so there is no amount-less QRPH code.
            return self.env._("The amount must be set to generate a QRPH code.")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == const.QR_METHOD:
            return self._l10n_ph_qrph_get_qr_code_body(amount, currency, free_communication, structured_communication)

        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == const.QR_METHOD:
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
        res_model = self.env.context.get('l10n_ph_qrph_model')
        res_id = self.env.context.get('l10n_ph_qrph_model_id')
        res_uuid = self.env.context.get('l10n_ph_qrph_model_uuid')
        company_id = self.env.context.get('l10n_ph_qrph_company_id') or self.env.company.id
        QrphTransaction = self.env['l10n_ph.qrph.transaction']

        # Refreshing the payment screen must not pile up payments on Maya's side.
        transaction = QrphTransaction._get_latest_transaction(res_model, res_id, company_id, res_uuid)
        if transaction and transaction._is_reusable(self, amount):
            return transaction.qr_code_body

        reference = (structured_communication or free_communication or '')[:36] or str(uuid.uuid4())
        response = self._l10n_ph_qrph_make_request(CREATE_PAYMENT_ENDPOINT, payload={
            'totalAmount': {
                'currency': currency.name,
                'value': float_repr(currency.round(amount), currency.decimal_places),
            },
            'requestReferenceNumber': reference,
        })

        if res_model and (res_id or res_uuid):
            # sudo: the cashier or the portal customer minting the transaction may not create it, and
            # only what Maya answered may end up in it.
            QrphTransaction.sudo().create({
                **QrphTransaction._get_record_vals(res_model, res_id, res_uuid),
                'bank_id': self.id,
                'company_id': company_id,
                'currency_id': currency.id,
                'amount': amount,
                'reference': reference,
                'maya_payment_id': response['paymentId'],
                'qr_code_body': response['qrCodeBody'],
            })

        return response['qrCodeBody']

    def _l10n_ph_qrph_fetch_payment_status(self, maya_payment_id):
        """ Return the status Maya reports for one of its payments, e.g. ``PAYMENT_SUCCESS``.

        :param str maya_payment_id: the identifier Maya gave the payment when the code was created
        :rtype: str
        """
        self.ensure_one()
        response = self._l10n_ph_qrph_make_request(PAYMENT_STATUS_ENDPOINT.format(payment_id=maya_payment_id))
        return response.get('status')

    def _l10n_ph_qrph_make_request(self, endpoint, payload=None):
        """ Call the Maya Business API with the credentials of this bank account.

        :param str endpoint: the path to call, relative to the Maya environment of this account
        :param dict payload: the JSON body to post; the request is a GET when there is none
        :return: the decoded JSON answer
        :rtype: dict
        """
        self.ensure_one()
        # sudo: only system users may see the key and the mode, but the codes are generated for portal
        # customers and cashiers. It is Maya's publishable key: it can request a payment, never move
        # money out of the account.
        bank = self.sudo()
        base_url = SANDBOX_URL if bank.l10n_ph_qrph_test_mode else PRODUCTION_URL
        try:
            response = requests.request(
                'POST' if payload else 'GET',
                urljoin(base_url, endpoint),
                json=payload,
                auth=(bank.l10n_ph_qrph_public_key, ''),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            raise MayaRequestError(self.env._("Maya refused the QRPH request: %s", error.response.text))
        except (requests.exceptions.RequestException, ValueError):
            raise MayaRequestError(self.env._("Could not establish a connection to the Maya API."))
