import urllib.parse
from odoo import api, models, _
from odoo.tools.urls import urljoin
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_qfpay import const


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of `payment` to ensure that QFPay's requirements for references are satisfied.

        QFPay's requirements for transaction are as follows:
        - References are safest when made of alphanumeric characters and/or '-' and '_'.
          The prefix is generated with 'tx' as default. This prevents the prefix from being
          generated based on document names that may contain non-allowed characters
          (e.g., INV/2025/...).

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code == 'qfpay':
            prefix = payment_utils.singularize_reference_prefix()

        return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_processing_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'qfpay':
            return res

        base_url = self.provider_id.get_base_url()

        payload = {
            'appcode': self.provider_id.qfpay_app_code,
            'sign_type': 'md5',
            'paysource': 'remotepay_checkout',
            'txamt': str(int(self.amount * 100)),
            'txcurrcd': self.currency_id.name,
            'out_trade_no': self.reference,
            'txdtm': self.create_date.strftime('%Y-%m-%d %H:%M:%S'),
            'return_url': urljoin(base_url, const.RETURN_URL),
            'failed_url': urljoin(base_url, const.RETURN_URL),
            'notify_url': urljoin(base_url, const.WEBHOOK_URL),
        }

        # Generate signature
        payload['sign'] = self.provider_id._qfpay_generate_sign(payload)
        api_base_url = self.provider_id._qfpay_get_api_url()
        query_string = urllib.parse.urlencode(payload)

        return {
            'api_url': f"{api_base_url}{query_string}",
            'url_params': {},
        }

    def _apply_updates(self, payment_data):
        """ Update the Odoo transaction state based on the payment data. """
        super()._apply_updates(payment_data)
        if self.provider_code != 'qfpay':
            return

        # Status Mapping
        response_code = payment_data.get('respcd')
        if response_code in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif response_code in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        else:
            error_msg = payment_data.get('respmsg', 'Unknown Error')
            self._set_error(_("QFPay Payment Failed: %s", error_msg))

    @api.model
    def _extract_reference(self, provider_code, notification_data):
        """ Override of `payment` to extract the reference from the payment data. """
        if provider_code != 'qfpay':
            return super()._extract_reference(provider_code, notification_data)
        return notification_data.get('out_trade_no')

    def _extract_amount_data(self, notification_data):
        """ Override of `payment` to extract the amount and currency from the payment data. """
        if self.provider_code != 'qfpay':
            return super()._extract_amount_data(notification_data)

        # QFPay sends the amount in cents (e.g., 77625 for $776.25)
        amount = float(notification_data.get('txamt', 0)) / 100.0
        return {
            'amount': amount,
            'currency_code': notification_data.get('txcurrcd'),
        }
