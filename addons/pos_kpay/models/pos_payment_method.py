# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import _, fields, models, api
from odoo.exceptions import UserError, AccessDenied, ValidationError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('kpay', 'KPay')]

    kpay_terminal_ip_address = fields.Char('KPay Terminal IP Address', copy=False)
    kpay_app_id = fields.Char('KPay App ID', copy=False)
    kpay_app_secret = fields.Char('KPay App Secret', copy=False)
    kpay_payment_type = fields.Selection([
        ('1', 'Credit Card/Debit Card'),
        ('2', 'QR Code'),
        ('3', 'QR Code Scanning'),
        ('4', 'Octopus'),
        ('5', 'Octopus QR Code'),
        ('6', 'PayMe QR Code'),
        ('7', 'PayMe QR Code Scanning'),
    ], 'KPay Payment Type', copy=False)

    kpay_latest_response = fields.Char(copy=False, groups='base.group_erp_manager')
    kpay_public_key = fields.Char('KPay Public Key', copy=False, groups='base.group_erp_manager')

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['kpay_terminal_ip_address', 'kpay_app_id', 'kpay_app_secret', 'kpay_payment_type']
        return params

    @api.constrains('kpay_app_id', 'kpay_payment_type')
    def _check_kpay_app_id(self):
        sudo_self = self.sudo()
        for payment_method in sudo_self:
            if not payment_method.kpay_app_id:
                continue
            existing_payment_method = sudo_self.search([('id', '!=', payment_method.id),
                                                        ('kpay_app_id', '=', payment_method.kpay_app_id),
                                                        ('kpay_payment_type', '=', payment_method.kpay_payment_type)],
                                                       limit=1)
            if existing_payment_method:
                raise ValidationError(_('Terminal %(terminal)s is already used on payment method %(payment_method)s.',
                                        terminal=payment_method.kpay_app_id, payment_method=existing_payment_method.display_name))

    @api.constrains('use_payment_terminal')
    def _check_kpay_terminal(self):
        if any(record.use_payment_terminal == 'kpay' and record.company_id.currency_id.name != 'HKD' for record in self):
            raise UserError(_('KPay is only valid for HKD Currency'))

    def kpay_set_public_key(self, public_key):
        self.kpay_public_key = public_key

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {'kpay_latest_response', 'kpay_public_key'})

    def get_latest_kpay_status(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        latest_response = self.sudo().kpay_latest_response
        latest_response = json.loads(latest_response) if latest_response else False
        return latest_response
