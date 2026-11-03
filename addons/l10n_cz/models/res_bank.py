import re

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.bank_account_number import get_iban_part, validate_iban


def _is_cz_mod11_valid(digits):
    # The prefix weights (10, 5, 8, 4, 2, 1) are the last 6 weights of the account number ones
    return sum(int(digit) * weight for digit, weight in zip(digits.zfill(10), (6, 3, 7, 9, 10, 5, 8, 4, 2, 1))) % 11 == 0


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _l10n_cz_get_domestic_account(self):
        """ Split a Czech account number, written either in the local format (prefix-number/bank-code)
        or as a Czech IBAN, into its domestic parts. Prefix and number must pass the Czech modulo 11 check.

        :return: a dict with the 'prefix' (empty if there is none), the 'number' and the 'bank_code'
        :raise ValidationError: if the account number is not a valid Czech account number
        """
        self.ensure_one()
        account_number = re.sub(r'\s+', '', self.account_number or '').upper()
        if account_number.startswith('CZ'):
            iban = validate_iban(self.env, account_number)
            prefix, number, bank_code = (get_iban_part(iban, part) for part in ('branch', 'account', 'bank'))
        elif match := re.fullmatch(r'(?:([0-9]{1,6})-)?([0-9]{1,10})/([0-9]{4})', account_number):
            prefix, number, bank_code = match.groups()
        else:
            raise ValidationError(self.env._('Use a Czech local account number (prefix-number/bank-code) or a Czech IBAN.'))

        if not _is_cz_mod11_valid(prefix or '') or not _is_cz_mod11_valid(number):
            raise ValidationError(self.env._('The account number does not pass the Czech modulo 11 check.'))
        return {
            'prefix': (prefix or '').lstrip('0'),
            'number': number.lstrip('0') or '0',
            'bank_code': bank_code,
        }

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'czk_qr':
            invoice = self.env['account.move'].search([
                *self.env['account.move']._check_company_domain(self.env.company),
                '|',
                ('payment_reference', '=', free_communication),
                ('name', '=', free_communication),
            ], limit=1)

            qr_code_vals = {
                'ACC': self.sanitized_account_number,                                                                   # Account Number
                'AM': amount,                                                                                           # Amount
                'CC': currency.name,                                                                                    # Currency
                'DT': invoice.invoice_date_due.strftime('%Y%m%d') if invoice and invoice.invoice_date_due else '',      # Due Date
                'MSG': free_communication[:60] if free_communication else '',                                           # Message for Recipient
                'RN': (self.holder_name or self.partner_id.name)[:35],                                                  # Recipient Name
                'PT': 'IP',                                                                                             # Payment Type
                'X-VS': re.sub(r'\D+', '', invoice.name) if invoice and invoice.name else '',                           # Variable Symbol
            }

            qr_code_data = "*".join(
                f"{key}:{value}"
                for key, value in qr_code_vals.items()
                if value
            )

            return f"SPD*1.0*{qr_code_data}*"
        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'czk_qr':
            return {
                'barcode_type': 'QR',
                'quiet': 0,
                'width': 128,
                'height': 128,
                'value': self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'czk_qr':
            error_messages = []
            if currency.id != self.env.ref('base.CZK').id:
                error_messages.append(self.env._("The bank account currency must be CZK to generate the QR code."))
            if self.account_type != 'iban':
                error_messages.append(self.env._("The bank account type must be IBAN to generate the QR code."))
            if not self.sanitized_account_number:
                error_messages.append(self.env._("An IBAN account number is required to generate the QR code."))
            if len(error_messages) > 0:
                return '\r\n'.join(error_messages)
            return None
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append(('czk_qr', self.env._("CZK QR"), 50))
        return rslt
