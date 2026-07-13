# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Endpoints of the API.
# See https://docs.adyen.com/api-explorer/#/CheckoutService/v70/overview for Checkout API
# See https://docs.adyen.com/api-explorer/#/Recurring/v68/overview for Recurring API
API_ENDPOINT_VERSIONS = {
    '/disable': 68,                 # Recurring API; unused - to remove
    '/paymentMethods': 71,          # Checkout API
    '/payments': 71,                # Checkout API
    '/payments/details': 71,        # Checkout API
    '/payments/{}/cancels': 71,     # Checkout API
    '/payments/{}/captures': 71,    # Checkout API
    '/payments/{}/refunds': 71,     # Checkout API
}

# Adyen-specific mapping of currency codes in ISO 4217 format to the number of decimals.
# Only currencies for which Adyen does not follow the ISO 4217 norm are listed here.
# See https://docs.adyen.com/development-resources/currency-codes
CURRENCY_DECIMALS = {
    'CLP': 2,
    'CVE': 0,
    'IDR': 0,
    'ISK': 2,
}

# The codes of the payment methods to activate when Adyen is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

# Mapping of payment method codes to Adyen codes.
PAYMENT_METHODS_MAPPING = {
    'ach_direct_debit': 'ach',
    'apple_pay': 'applepay',
    'bacs_direct_debit': 'directdebit_GB',
    'bancontact_card': 'bcmc',
    'bancontact': 'bcmc_mobile',
    'cash_app_pay': 'cashapp',
    'gopay': 'gopay_wallet',
    'becs_direct_debit': 'au_becs_debit',
    'afterpay': 'afterpaytouch',
    'klarna_pay_over_time': 'klarna_account',
    'momo': 'momo_wallet',
    'napas_card': 'momo_atm',
    'paytrail': 'ebanking_FI',
    'online_banking_czech_republic': 'onlineBanking_CZ',
    'online_banking_india': 'onlinebanking_IN',
    'fpx': 'molpay_ebanking_fpx_MY',
    'p24': 'onlineBanking_PL',
    'mastercard': 'mc',
    'online_banking_slovakia': 'onlineBanking_SK',
    'online_banking_thailand': 'molpay_ebanking_TH',
    'open_banking': 'paybybank',
    'samsung_pay': 'samsungpay',
    'sepa_direct_debit': 'sepadirectdebit',
    'sofort': 'directEbanking',
    'unionpay': 'cup',
    'wallets_india': 'wallet_IN',
    'wechat_pay': 'wechatpayQR',
}

# Mapping of transaction states to Adyen result codes.
# See https://docs.adyen.com/checkout/payment-result-codes for the exhaustive list of result codes.
RESULT_CODES_MAPPING = {
    'pending': (
        'ChallengeShopper', 'IdentifyShopper', 'Pending', 'PresentToShopper', 'Received',
        'RedirectShopper'
    ),
    'done': ('Authorised',),
    'cancel': ('Cancelled',),
    'error': ('Error',),
    'refused': ('Refused',),
}
