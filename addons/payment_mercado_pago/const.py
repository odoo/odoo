# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Currency codes of the currencies supported by Mercado Pago in ISO 4217 format.
# See https://api.mercadopago.com/currencies. Last seen online: 24 November 2022.
SUPPORTED_CURRENCIES = [
    'ARS',  # Argentinian Peso
    'BOB',  # Boliviano
    'BRL',  # Real
    'CLF',  # Fomento Unity
    'CLP',  # Chilean Peso
    'COP',  # Colombian Peso
    'CRC',  # Colon
    'CUC',  # Cuban Convertible Peso
    'CUP',  # Cuban Peso
    'DOP',  # Dominican Peso
    'EUR',  # Euro
    'GTQ',  # Guatemalan Quetzal
    'HNL',  # Lempira
    'MXN',  # Mexican Peso
    'NIO',  # Cordoba
    'PAB',  # Balboa
    'PEN',  # Sol
    'PYG',  # Guarani
    'USD',  # US Dollars
    'UYU',  # Uruguayan Peso
    'VEF',  # Strong Bolivar
    'VES',  # Sovereign Bolivar
]

# The codes of the payment methods to activate when Mercado Pago is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'argencard',
    'ceconsud',
    'cordobesa',
    'codensa',
    'lider',
    'magna',
    'naranja',
    'nativa',
    'oca',
    'presto',
    'tarjeta_mercadopago',
    'shopping',
    'elo',
    'hipercard',
]

# Mapping of payment method codes to Mercado Pago codes.
PAYMENT_METHODS_MAPPING = {
    'card': 'debit_card,credit_card,prepaid_card',
    'paypal': 'digital_wallet',
}

# Mapping of transaction states to Mercado Pago payment statuses.
# See https://www.mercadopago.com.mx/developers/en/reference/payments/_payments_id/get.
TRANSACTION_STATUS_MAPPING = {
    'pending': ('pending', 'in_process', 'in_mediation'),
    'done': ('approved', 'refunded'),
    'canceled': ('cancelled', 'null'),
}
