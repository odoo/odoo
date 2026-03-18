import hashlib
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.payment_qfpay import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('qfpay', "QFPay")], ondelete={'qfpay': 'set default'})
    qfpay_app_code = fields.Char(string="App Code", required_if_provider="qfpay")
    qfpay_app_key = fields.Char(string="App Key", required_if_provider="qfpay", groups='base.group_system')
    qfpay_mchntid = fields.Char(string="Merchant ID")

    def _qfpay_get_api_url(self):
        """ Return the redirect URL based on state. """
        self.ensure_one()
        if self.state == 'enabled':
            return const.API_URLS.get('enabled')
        return const.API_URLS.get('test')

    def _qfpay_generate_sign(self, values):
        """ Generate signature by sorting ASCII keys and appending key. """
        self.ensure_one()
        items = sorted([(k, str(v)) for k, v in values.items() if v and k not in ('sign', 'lang')])
        query_string = '&'.join([f"{k}={v}" for k, v in items])
        signing_string = f"{query_string}{self.qfpay_app_key}"
        return hashlib.md5(signing_string.encode('utf-8')).hexdigest()

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'qfpay':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CONSTRAINT METHODS === #

    @api.constrains('available_currency_ids')
    def _check_available_currency_ids_only_contains_supported_currencies(self):
        """ Ensure that only supported currencies can be selected in the backend. """
        for provider in self.filtered(lambda p: p.code == 'qfpay'):
            unsupported_currencies = provider.available_currency_ids.filtered(
                lambda c: c.name not in const.SUPPORTED_CURRENCIES
            )
            if unsupported_currencies:
                supported_list = ", ".join(const.SUPPORTED_CURRENCIES)
                raise ValidationError(
                    _("QFPay only supports the following currencies: %s", supported_list)
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Return the payment method codes to activate by default. """
        res = super()._get_default_payment_method_codes()
        if self.code != 'qfpay':
            return res

        codes = const.DEFAULT_PAYMENT_METHOD_CODES
        supported_codes = []
        for code in codes:
            is_apple_pay = "apple" in code.lower()
            # Apple Pay is not supported at the moment.
            if is_apple_pay:
                continue
            supported_codes.append(code)

        return supported_codes
