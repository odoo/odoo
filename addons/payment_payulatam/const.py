# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Supported currencies of PayuLatam, in ISO 4217 currency codes.
# https://developers.payulatam.com/latam/en/docs/getting-started/response-codes-and-variables.html#accepted-currencies.
# Last seen online: 22 September 2022.
SUPPORTED_CURRENCIES = [
    'ARS',
    'BRL',
    'CLP',
    'COP',
    'MXN',
    'PEN',
    'USD'
]

# The codes of the payment methods to activate when PayULatam is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

# Mapping of payment method codes to PayU Latam codes.
PAYMENT_METHODS_MAPPING = {
    'bank_reference': 'BANK_REFERENCED',
    'pix': 'PIX',
    'card': 'VISA,VISA_DEBIT,MASTERCARD,MASTERCARD_DEBIT,AMEX,ARGENCARD,CABAL,CENCOSUD,DINERS,ELO,NARANJA,SHOPPING,HIPERCARD,TRANSBANK_DEBIT,CODENSA',
    'bank_transfer': 'ITAU,PSE,SPEI',
}
