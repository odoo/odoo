# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Currency codes of the currencies supported by Mercado Pago in ISO 4217 format.
# See https://api.mercadopago.com/currencies.
SUPPORTED_CURRENCIES = [
    'ARS',  # Argentinian Peso
    'BRL',  # Real
    'CLP',  # Chilean Peso
    'CLF',  # Fomento Unity
    'MXN',  # Mexican Peso
    'COP',  # Colombian Peso
    'CRC',  # Colon
    'CUC',  # Cuban Convertible Peso
    'CUP',  # Cuban Peso
    'DOP',  # Dominican Peso
    'GTQ',  # Guatemalan Quetzal
    'HNL',  # Lempira
    'NIO',  # Cordoba
    'PAB',  # Balboa
    'PEN',  # Sol
    'PYG',  # Guarani
    'USD',  # US Dollars
    'UYU',  # Uruguayan Peso
    'VEF',  # Strong Bolivar
    'VES',  # Sovereign Bolivar
]

# Mapping of transaction states to Mercado Pago payment statuses.
# See https://www.mercadopago.com.mx/developers/en/reference/payments/_payments_id/get.
TRANSACTION_STATUS_MAPPING = {
    'pending': ('pending', 'in_process', 'in_mediation'),
    'done': ('approved', 'refunded'),
    'canceled': ('cancelled', 'null'),
}
