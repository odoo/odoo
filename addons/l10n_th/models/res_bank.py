# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    proxy_type = fields.Selection(selection_add=[('ewallet_id', 'Ewallet ID'),
                                                 ('merchant_tax_id', 'Merchant Tax ID'),
                                                 ('mobile', "Mobile Number")],
                                  ondelete={'ewallet_id': 'set default', 'merchant_tax_id': 'set default', 'mobile': 'set default'})

    @api.constrains('proxy_type', 'proxy_value', 'partner_id')
    def _check_th_proxy(self):
        tax_id_re = re.compile(r'^[0-9]{13}$')
        mobile_re = re.compile(r'^[0-9]{10}$')
        for bank in self.filtered(lambda b: b.country_code == 'TH'):
            if bank.proxy_type not in ['ewallet_id', 'merchant_tax_id', 'mobile', 'none', False]:
                raise ValidationError(_("The QR Code Type must be either Ewallet ID, Merchant Tax ID or Mobile Number to generate a Thailand Bank QR code for account number %s.", bank.acc_number))
            if bank.proxy_type == 'merchant_tax_id' and (not bank.proxy_value or not tax_id_re.match(bank.proxy_value)):
                raise ValidationError(_("The Merchant Tax ID must be in the format 1234567890123 for account number %s.", bank.acc_number))
            if bank.proxy_type == 'mobile' and (not bank.proxy_value or not mobile_re.match(bank.proxy_value)):
                raise ValidationError(_("The Mobile Number must be in the format 0812345678 for account number %s.", bank.acc_number))

    @api.depends('country_code')
    def _compute_country_proxy_keys(self):
        bank_th = self.filtered(lambda b: b.country_code == 'TH')
        bank_th.country_proxy_keys = 'ewallet_id,merchant_tax_id,mobile'
        super(ResPartnerBank, self - bank_th)._compute_country_proxy_keys()

    @api.depends('country_code')
    def _compute_display_qr_setting(self):
        bank_th = self.filtered(lambda b: b.country_code == 'TH')
        bank_th.display_qr_setting = True
        super(ResPartnerBank, self - bank_th)._compute_display_qr_setting()

    def _get_merchant_account_info(self):
        if self.country_code == 'TH':
            proxy_type_mapping = {
                'mobile': 1,
                'merchant_tax_id': 2,
                'ewallet_id': 3,
            }
            proxy_value = re.sub(r"^0", "66", self.proxy_value).zfill(13) if self.proxy_type == 'mobile' else self.proxy_value
            vals = [
                (0, 'A000000677010111'),
                (proxy_type_mapping[self.proxy_type], proxy_value),
            ]
            return (29, ''.join([self._serialize(*val) for val in vals]))
        return super()._get_merchant_account_info()

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'emv_qr' and self.country_code == 'TH':
            if currency.name not in ['THB']:
                return _("Can't generate a PayNow QR code with a currency other than THB.")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr' and self.country_code == 'TH' and self.proxy_type not in ['ewallet_id', 'merchant_tax_id', 'mobile']:
            return _("The PayNow Type must be either Ewallet ID, Merchant Tax ID or Mobile Number to generate a Thailand Bank QR code")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
