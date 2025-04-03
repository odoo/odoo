# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment methods to activate when Redsys is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods
    'card',
    'bizum',
    # Brand payment methods
    'visa',
    'mastercard',
    'amex',
    'diners',
    'jcb',
}

# Mapping of payment method codes to Redsys codes.
PAYMENT_METHODS_MAPPING = {
    'bizum': 'z',
    'card': 'C',
    'visa': '1',
    'mastercard': '2',
    'amex': '8',
    'diners': '6',
    'jcb': '9',
}

# Mapping of transaction states to Redsys payment statuses.
# See https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/parametros-de-entrada-y-salida/.
PAYMENT_STATUS_MAPPING = {
    'done': tuple(f'{i:04}' for i in range(100)) + ('400', '900'),  # From 0000 to 0099, 400 and 900
    'cancel': (
        '9915',
    ),
    'error': (
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
        '9997',
        '9998',
        '9999',
    ),
}
