# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Mapping of transaction states to Redsys payment statuses.
# See https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/parametros-de-entrada-y-salida/
PAYMENT_STATUS_MAPPING = {
    'done': tuple(f'{i:04}' for i in range(100)),  # From 0000 to 0099
    'authorized': ('900', '400'),
    'cancel': (
        '101',
        '102',
        '106',
        '125',
        '129',
        '172',
        '173',
        '174',
        '180',
        '184',
        '190',
        '191',
        '195',
        '202',
    ),
    'error': (
        '904',
        '909',
        '913',
        '944',
        '950',
        '9912',
        '912',
        '9064',
        '9078',
        '9093',
        '9094',
        '9104',
        '9218',
        '9253',
        '9256',
        '9257',
        '9261',
        '9915',
        '9997',
        '9998',
        '9999',
    ),
}

# The codes of the payment methods to activate when Redsys is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods
    'card',
    'bizum',
}

# Mapping of payment method codes to Redsys codes.
PAYMENT_METHODS_MAPPING = {
    'card': 'C',
    'bizum': 'z',
}
