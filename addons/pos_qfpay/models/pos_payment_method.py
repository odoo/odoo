# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from odoo import _, fields, models, api
from odoo.exceptions import UserError, AccessDenied


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('qfpay', 'QFPay')]

    qfpay_terminal_ip_address = fields.Char('QFPay Terminal IP Address', copy=False)
    qfpay_pos_key = fields.Char('QFPay POS Key', copy=False, groups='point_of_sale.group_pos_manager')
    qfpay_notification_key = fields.Char(string='QFPay Notification Key', copy=False, groups='point_of_sale.group_pos_manager')
    qfpay_latest_response = fields.Char(copy=False, groups='point_of_sale.group_pos_manager')
    qfpay_payment_type = fields.Selection([
        ('card_payment', 'Visa/Mastercard'),
        ('wx', 'WeChat Pay'),
        ('alipay', 'Alipay'),
        ('payme', 'PayMe'),
        ('union', 'UnionPay QuickPass'),
        ('fps', 'FPS'),
        ('octopus', 'Octopus'),
        ('unionpay_card', 'Unionpay Card'),
        ('amex_card', 'American Express Card'),
    ], 'QFPay Payment Type', copy=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['qfpay_terminal_ip_address', 'qfpay_payment_type']
        return params

    @api.constrains('use_payment_terminal')
    def _check_qfpay_terminal(self):
        if any(record.use_payment_terminal == 'qfpay' and record.company_id.currency_id.name != 'HKD' for record in self):
            raise UserError(_('QFPay is only valid for HKD Currency'))

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {'qfpay_latest_response'})

    def qfpay_sign_request(self, payload):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        if self.use_payment_terminal != 'qfpay':
            raise UserError(_('This method can only be used with QFPay payment terminal.'))

        key = self.sudo().qfpay_pos_key
        # AES IV is a constant as stated in the documentation
        aes_iv = 'qfpay202306_hjsh'

        # Sort the payload items and format
        payload_items = sorted((k, '' if v is None else v) for k, v in payload.items())
        formated_payload = ','.join(f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}" for k, v in payload_items)
        formated_payload = '{' + formated_payload + '}'

        # Generate Digest
        md5 = hashlib.md5()
        md5.update((formated_payload + key).encode('utf-8'))
        digest = md5.hexdigest().upper()

        # Prepare the payload to encrypt
        payload_to_encrypt = "{content:" + formated_payload + ", digest:'" + digest + "'}"

        # Encrypt the payload
        cipher = Cipher(algorithms.AES(key.encode('utf-8')), modes.CBC(aes_iv.encode('utf-8')))
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(payload_to_encrypt.encode('utf-8')) + padder.finalize()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted).decode('utf-8')

    @api.model
    def _qfpay_handle_webhook(self, config, data, uuid):
        config._notify("QFPAY_LATEST_RESPONSE", {
            'response': data,
            'line_uuid': uuid,
        })
