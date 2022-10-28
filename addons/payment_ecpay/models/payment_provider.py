# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.payment_ecpay.utils.ecpay_payment_sdk import ECPayPaymentSdk

class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[('ecpay', "ECPay")], ondelete={'ecpay': 'set default'}
    )
    ecpay_merchant_id = fields.Char(
        string="ECPay Merchant ID",
        help="The Merchant ID solely used to identify your ECPay account.",
        required_if_provider="ecpay",
    )
    ecpay_hash_key = fields.Char(
        string="ECPay Secure Hash Key",
        required_if_provider="ecpay",
        groups='base.group_system',
    )
    ecpay_hash_iv = fields.Char(
        string="ECPay Secure Hash IV",
        required_if_provider="ecpay",
        groups='base.group_system',
    )

    # === BUSINESS METHODS ===#

    def _ecpay_get_api_url(self):
        """ Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'enabled':
            return "https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5"
        else:   # 'test'
            return "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"

    def _ecpay_calculate_signature(self, data, incoming=True):
        """ Compute the signature for the provided data using ECPay SDK.

        :param dict data: The data to sign.
        :return: The calculated signature.
        :rtype: str
        """
        PaymentHelper = ECPayPaymentSdk(
            self.ecpay_merchant_id, self.ecpay_hash_key, self.ecpay_hash_iv
        )
        signature_function = PaymentHelper.generate_check_value if incoming else PaymentHelper.create_order
        return signature_function(data)
