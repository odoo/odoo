from odoo import models, fields
import hmac
import hashlib

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    api_key = fields.Char(string='178011212167efc7628d1cf3.91649419', required=True)
    site_id = fields.Char(string='105891419', required=True)


    def _get_specific_rendering_values(self, processing_values):
        self.ensure_one()
        return {
            'api_key': self.provider_id.cinetpay_api_key,
            'site_id': self.provider_id.cinetpay_site_id,
            'transaction_id': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'description': self.reference,
            'return_url': self.get_return_url(),
            'notify_url': self.provider_id.cinetpay_notify_url,
        }

    def _handle_notification_data(self, provider_code, data):
        self.ensure_one()
        if provider_code == 'cinetpay':
            if data.get('status') == 'ACCEPTED':
                self._set_transaction_done()
            elif data.get('status') == 'REFUSED':
                self._set_transaction_cancel()
            else:
                self._set_transaction_pending()
