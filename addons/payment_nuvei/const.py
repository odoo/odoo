# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Nuvei, in ISO 4217 format.
SUPPORTED_CURRENCIES = [
    'ARS',
    'BRL',
    'CAD',
    'CLP',
    'COP',
    'MXN',
    'PEN',
    'USD',
    'UYU',
]

# The codes of the payment methods to activate when Nuvei is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
    'tarjeta_mercadopago',
    'naranja',
}

# Some payment methods require no decimal points no matter the currency
INTEGER_METHODS = [
    'webpay',
]

# Some payment methods require first and last name on customers to work.
FULL_NAME_METHODS = [
    'boleto',
]

# Mapping of payment method codes to Nuvei codes.
PAYMENT_METHODS_MAPPING = {
    'astropay': 'apmgw_Astropay_TEF',
    'boleto': 'apmgw_BOLETO',
    'card': 'cc_card',
    'nuvei_local': 'apmgw_Local_Payments',
    'oxxopay': 'apmgw_OXXO_PAY',
    'pix': 'apmgw_PIX',
    'pse': 'apmgw_PSE',
    'spei': 'apmgw_SPEI',
    'webpay': 'apmgw_Webpay',
}

# The keys of the values to use in the calculation of the signature.
SIGNATURE_KEYS = [
    'totalAmount',
    'currency',
    'responseTimeStamp',
    'PPP_TransactionID',
    'Status',
    'productId',
]

# Mapping of transaction states to Nuvei payment statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': ('pending',),
    'done': ('approved', 'ok',),
    'error': ('declined', 'error', 'fail',),
}
