# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (c) 2026 Data Dance s.r.o. (https://www.datadance.eu)
import base64
import binascii
import lzma
import re

from odoo import api, fields, models
from odoo.tools import float_repr

# PAY by square is the payment QR-code standard of the Slovak Banking
# Association; it is understood by every Slovak banking application.
# The specification is available at
# https://www.sbaonline.sk/wp-content/uploads/2020/03/pay-by-square-specifications-1_1_0.pdf
# The code is a tab-separated data model (table 15 of the specification),
# prefixed with its CRC-32, compressed with raw LZMA1 and finally encoded in
# base32hex. Maximum lengths below are the ones imposed by that data model.
L10N_SK_QR_MAX_VARIABLE_SYMBOL = 10
L10N_SK_QR_MAX_PAYMENT_NOTE = 140
L10N_SK_QR_MAX_BENEFICIARY_NAME = 70


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _l10n_sk_encode_pay_by_square(self, payment_data):
        """ Encode a PAY by square data model into the string a QR-code is made of.

        :param payment_data: the tab-separated data model, as described by table 15
                             of the PAY by square specification
        :return: the base32hex representation of the compressed, check-summed payload
        """
        payload = payment_data.encode()
        # The CRC-32 is stored little-endian in front of the data it covers.
        checked_payload = binascii.crc32(payload).to_bytes(4, 'little') + payload
        compressed = lzma.compress(checked_payload, format=lzma.FORMAT_RAW, filters=[{
            'id': lzma.FILTER_LZMA1,
            'lc': 3,
            'lp': 0,
            'pb': 2,
            'dict_size': 128 * 1024,
        }])
        # Two reserved null bytes, then the uncompressed length, little-endian.
        header = b'\x00\x00' + len(checked_payload).to_bytes(2, 'little')
        return base64.b32hexencode(header + compressed).decode().rstrip('=')

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'sk_qr':
            communication = structured_communication or free_communication or ''
            # Slovak banks reconcile incoming payments on the variable symbol,
            # which is numeric only; keep the last digits of the reference so
            # that the sequence number survives the truncation.
            variable_symbol = re.sub(r'\D', '', communication)[-L10N_SK_QR_MAX_VARIABLE_SYMBOL:]
            # The due date is not part of the generic QR-code signature; invoices
            # pass it along through the context (see l10n_sk/models/account_move.py).
            # PaymentDueDate is an optional field of the data model (specification,
            # appendix B, 2.4), so it stays empty when no due date is known.
            due_date = self.env.context.get('invoice_date_due')
            payment_data = '\t'.join([
                '',                                                             # InvoiceID
                '1',                                                            # Payments: a single one
                '1',                                                            # PaymentOptions: pay order
                float_repr(currency.round(amount), currency.decimal_places),    # Amount
                currency.name,                                                  # CurrencyCode
                fields.Date.to_date(due_date).strftime('%Y%m%d') if due_date else '',   # PaymentDueDate
                variable_symbol,                                                # VariableSymbol
                '',                                                             # ConstantSymbol
                '',                                                             # SpecificSymbol
                '',                                                             # OriginatorsReferenceInformation, mutually exclusive with the symbols above
                communication[:L10N_SK_QR_MAX_PAYMENT_NOTE],                    # PaymentNote
                '1',                                                            # BankAccounts: a single one
                self.sanitized_account_number,                                  # IBAN
                self.bank_bic or '',                                            # BIC
                '0',                                                            # StandingOrderExt: not a standing order
                '0',                                                            # DirectDebitExt: not a direct debit
                (self.holder_name or self.partner_id.name)[:L10N_SK_QR_MAX_BENEFICIARY_NAME],   # BeneficiaryName
                '',                                                             # BeneficiaryAddressLine1
                '',                                                             # BeneficiaryAddressLine2
            ])
            return self._l10n_sk_encode_pay_by_square(payment_data)
        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'sk_qr':
            return {
                'barcode_type': 'QR',
                'quiet': 0,
                'width': 128,
                'height': 128,
                'value': self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        # EXTENDS account
        if qr_method == 'sk_qr':
            error_messages = []
            if self.country_code != 'SK':
                error_messages.append(self.env._("The bank account must be located in Slovakia to generate a PAY by square QR code."))
            if currency.name != 'EUR':
                error_messages.append(self.env._("The currency must be EUR to generate a PAY by square QR code."))
            if self.account_type != 'iban':
                error_messages.append(self.env._("The bank account type must be IBAN to generate a PAY by square QR code."))
            return '\r\n'.join(error_messages) or None
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'sk_qr' and not self.holder_name and not self.partner_id.name:
            return self.env._("The account receiving the payment must have an account holder name or partner name set.")
        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    @api.model
    def _get_available_qr_methods(self):
        # EXTENDS account
        rslt = super()._get_available_qr_methods()
        # Slovak banking applications read PAY by square rather than the EPC
        # SEPA QR-code, so it comes first for the accounts it is eligible for.
        rslt.append(('sk_qr', self.env._("PAY by square"), 15))
        return rslt
