# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Nuvei, in ISO 4217 format.
SUPPORTED_CURRENCIES = [
    'ARS',
    'BRL',
    'CLP',
    'COP',
    'MXN',
    'PEN',
    'USD',
]

# Mapping of transaction states to Nuvei payment statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': ('pending',),
    'done': ('approved',),
    'error': ('declined', 'error', 'fail'),
}

# The codes of the payment methods to activate when Nuvei is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    'boleto',
    'pix',
    'astropay',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
    'tarjeta_mercadopago',
    'naranja',
    # Bank reference brands.
    'banco_guayaquil',
    'banco_pichincha',
    'facilito',
    'tia'

}

# Some payment methods require no decimal points no matter the currency
INTEGER_METHODS = [
    'webpay'
]

# Mapping of payment method codes to Nuvei codes.
PAYMENT_METHODS_MAPPING = {
    'astropay': 'apmgw_Astropay_TEF',
    'boleto': 'apmgw_BOLETO',
    'card': 'cc_card',
    'oxxopay': 'apmgw_OXXO_PAY',
    'pagofacil': 'apmgw_PagoFacil',
    'pix': 'apmgw_PIX',
    'pse': 'apmgw_PSE',
    'rapipago': 'apmgw_rapipago',
    'spei': 'apmgw_SPEI',
    'webpay': 'apmgw_Webpay'
}

# The keys of the values to use in the calculation of the signature.
INCOMING_KEYS = [
    'totalAmount',
    'currency',
    'responseTimeStamp',
    'PPP_TransactionID',
    'Status',
    'productId',
]
