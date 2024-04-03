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
# See https://docs.mollie.com/payments/multicurrency
SUPPORTED_CURRENCIES = [
    'AED', 'AUD', 'BGN', 'BRL', 'CAD', 'CHF',
    'CZK', 'DKK', 'EUR', 'GBP', 'HKD', 'HRK',
    'HUF', 'ILS', 'ISK', 'JPY', 'MXN', 'MYR',
    'NOK', 'NZD', 'PHP', 'PLN', 'RON', 'RUB',
    'SEK', 'SGD', 'THB', 'TWD', 'USD', 'ZAR'
]
