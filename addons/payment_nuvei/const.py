# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
    'paypal',
    'boleto',
    'pix',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
    'tarjeta_mercadopago',
    'naranja',

}

# Mapping of payment method codes to Nuvei codes.
PAYMENT_METHODS_MAPPING = {
    'boleto': 'apmgw_BOLETO',
    'boleto_rapido': 'apmgw_BOLETO_RAPIDO',
    'card': 'cc_card',
    'oxxopay': 'apmgw_OXXO_PAY',
    'pagofacil': 'apmgw_PagoFacil',
    'paypal': 'apmgw_expresscheckout',
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
