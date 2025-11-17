# Part of Odoo. See LICENSE file for full copyright and licensing details.

# List of ISO 15897 locale supported by Mollie
# See full details at `locale` parameter at https://docs.mollie.com/reference/v2/payments-api/create-payment
SUPPORTED_LOCALES = [
    'en_US', 'nl_NL', 'nl_BE', 'fr_FR',
    'fr_BE', 'de_DE', 'de_AT', 'de_CH',
    'es_ES', 'ca_ES', 'pt_PT', 'it_IT',
    'nb_NO', 'sv_SE', 'fi_FI', 'da_DK',
    'is_IS', 'hu_HU', 'pl_PL', 'lv_LV',
    'lt_LT'
]

# Currency codes in ISO 4217 format supported by mollie.
# Note: support varies per payment method.
# See https://docs.mollie.com/payments/multicurrency. Last seen online: 22 September 2022.
SUPPORTED_CURRENCIES = [
    'AED',
    'AUD',
    'BGN',
    'BRL',
    'CAD',
    'CHF',
    'CZK',
    'DKK',
    'EUR',
    'GBP',
    'HKD',
    'HRK',
    'HUF',
    'ILS',
    'ISK',
    'JPY',
    'MXN',
    'MYR',
    'NOK',
    'NZD',
    'PHP',
    'PLN',
    'RON',
    'RUB',
    'SEK',
    'SGD',
    'THB',
    'TWD',
    'USD',
    'ZAR'
]

# The codes of the payment methods to activate when Mollie is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
}

# Mapping of payment method codes to Mollie codes.
PAYMENT_METHODS_MAPPING = {
    'apple_pay': 'applepay',
    'card': 'creditcard',
    'bank_transfer': 'banktransfer',
    'kbc_cbc': 'kbc',
    'p24': 'przelewy24',
    'sepa_direct_debit': 'directdebit',
}
