# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    proxy_type = fields.Selection(selection_add=[('merchant_id', 'Merchant ID'),
                                                 ('payment_service', 'Payment Service'),
                                                 ('atm_card', 'ATM Card Number'),
                                                 ('bank_acc', 'Bank Account')],
                                  ondelete={'merchant_id': 'set default', 'payment_service': 'set default', 'atm_card': 'set default', 'bank_acc': 'set default'})

    @api.constrains('proxy_type')
    def _check_vn_proxy(self):
        for bank in self.filtered(lambda b: b.country_code == 'VN'):
            if bank.proxy_type not in ['merchant_id', 'payment_service', 'atm_card', 'bank_acc', 'none', False]:
                raise ValidationError(_("The QR Code Type must be either Merchant ID, ATM Card Number or Bank Account to generate a Vietnam Bank QR code for account number %s.", bank.acc_number))

    @api.depends('country_code')
    def _compute_display_qr_setting(self):
        bank_vn = self.filtered(lambda b: b.country_code == 'VN')
        bank_vn.display_qr_setting = self.env.company.qr_code
        super(ResPartnerBank, self - bank_vn)._compute_display_qr_setting()

    def _get_merchant_account_info(self):
        if self.country_code == 'VN':
            proxy_type_mapping = {
                'merchant_id': 'QRPUSH',
                'payment_service': 'QRPUSH',
                'atm_card': 'QRIBFTTC',
                'bank_acc': 'QRIBFTTA',
            }
            payment_network = [
                (0, self.bank_bic),
                (1, self.proxy_value),
            ]
            vals = [
                (0, 'A000000727'),
                (1, ''.join([self._serialize(*val) for val in payment_network])),
                (2, proxy_type_mapping[self.proxy_type]),
            ]
            return (38, ''.join([self._serialize(*val) for val in vals]))
        return super()._get_merchant_account_info()

    def _get_additional_data_field(self, comment):
        if self.country_code == 'VN':
            # The first check is too permissive for VietQR.
            return self._serialize(8, re.sub(r"[^a-zA-Z0-9 _\\\-.]+", "", comment))
        return super()._get_additional_data_field(comment)

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'emv_qr' and self.country_code == 'VN':
            if currency.name not in ['VND']:
                return _("Can't generate a Vietnamese QR banking code with a currency other than VND.")
            if not self.bank_bic:
                return _("Missing Bank Identifier Code.\n"
                         "Please configure the Bank Identifier Code inside the bank settings.")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr' and self.country_code == 'VN' and self.proxy_type not in ['merchant_id', 'payment_service', 'atm_card', 'bank_acc']:
            return _("The proxy type %s is not supported for Vietnamese partners. It must be either Merchant ID, ATM Card Number or Bank Account", self.proxy_type)

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
