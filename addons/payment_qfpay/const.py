# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

SENSITIVE_KEYS = {'qfpay_app_key'}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

RETURN_URL = '/payment/qfpay/return'
WEBHOOK_URL = '/payment/qfpay/webhook'
STATUS_URL = '/payment/status'

SUPPORTED_CURRENCIES = [
    'HKD',
    'CNY',
    'USD',
]

DEFAULT_PAYMENT_METHOD_CODES = [
    'alipay',
    'alipay_hk',
    'wechat_pay',
    'unionpay',
    'fps',
    'payme',
    'card',
    'apple_pay',
]

PAYMENT_STATUS_MAPPING = {
    'done': ['0000'],
    'pending': ['1143', '1145'],
}

# URLs for different environments.
API_URLS = {
    'enabled': 'https://test-openapi-hk.qfapi.com/checkstand/#/?',
    'test': 'https://openapi-int.qfapi.com/checkstand/#/?',
}
