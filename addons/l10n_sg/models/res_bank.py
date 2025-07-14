# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    proxy_type = fields.Selection(selection_add=[('mobile', 'Mobile Number'), ('uen', 'UEN')],
                                  ondelete={'mobile': 'set default', 'uen': 'set default'})

    @api.constrains('proxy_type', 'proxy_value', 'partner_id')
    def _check_sg_proxy(self):
        for bank in self.filtered(lambda b: b.country_code == 'SG'):
            if bank.proxy_type not in ['mobile', 'uen', 'none', False]:
                raise ValidationError(_("The PayNow Type must be either Mobile or UEN to generate a PayNow QR code for account number %s.", bank.acc_number))

    @api.depends('country_code')
    def _compute_country_proxy_keys(self):
        bank_sg = self.filtered(lambda b: b.country_code == 'SG')
        bank_sg.country_proxy_keys = 'mobile,uen'
        super(ResPartnerBank, self - bank_sg)._compute_country_proxy_keys()

    @api.depends('country_code')
    def _compute_display_qr_setting(self):
        bank_sg = self.filtered(lambda b: b.country_code == 'SG')
        bank_sg.display_qr_setting = True
        super(ResPartnerBank, self - bank_sg)._compute_display_qr_setting()

    def _get_merchant_account_info(self):
        if self.country_code == 'SG':
            proxy_type_mapping = {
                'mobile': 0,
                'uen': 2,
            }
            merchant_account_vals = [
                (0, 'SG.PAYNOW'),                                           # GUID
                (1, proxy_type_mapping[self.proxy_type]),                   # Proxy Type
                (2, self.proxy_value),                                      # Proxy Value
                (3, 0),                                                     # Is Amount Editable
            ]
            merchant_account_info = ''.join([self._serialize(*val) for val in merchant_account_vals])
            return (26, merchant_account_info)
        return super()._get_merchant_account_info()

    def _get_additional_data_field(self, comment):
        if self.country_code == 'SG':
            return self._serialize(1, comment)
        return super()._get_additional_data_field(comment)

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'emv_qr' and self.country_code == 'SG':
            if currency.name not in ['SGD']:
                return _("Can't generate a PayNow QR code with a currency other than SGD.")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'emv_qr' and self.country_code == 'SG' and self.proxy_type not in ['mobile', 'uen']:
            return _("The PayNow Type must be either Mobile Number or UEN.")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
