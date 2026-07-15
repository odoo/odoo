import re

from odoo import models, api


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'czk_qr':
            invoice = self.env['account.move'].search([
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
