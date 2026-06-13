# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__, default_lang="en_US")

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

# Mapping of Redsys error codes to generic error messages. Error codes are received with 4-digits.
# See https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/parametros-de-entrada-y-salida/#tablepress-11_wrapper
ERROR_CODE_GROUPS = {
    (102, 115, 129, 191, 201, 9064, 9093, 9253): _lt("Invalid card details."),
    (110, 116, 121, 162, 193, 9261): _lt("Insufficient funds or limit exceeded."),
    (106, 112, 117, 123, 126, 184, 187, 195, 206, 9104, 9999): _lt("Authentication failed."),
    (104, 114, 130, 204, 950, 9078, 9218, 9256, 9257): _lt(
        "Operation not allowed for this card or payment method."
    ),
    (101, 107, 118, 125, 163, 171, 172, 173, 174, 180, 181, 182, 190, 202, 290, 9094): _lt(
        "Transaction declined by the bank."
    ),
    (904, 909, 912, 913, 940, 941, 944, 945, 965, 9997, 9998): _lt(
        "Technical error. Please try again later."
    ),
}
ERROR_CODE_MAPPING = {
    f"{code:04}": msg for codes, msg in ERROR_CODE_GROUPS.items() for code in codes
}

# Mapping of transaction states to Redsys payment statuses.
# See https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/parametros-de-entrada-y-salida/.
PAYMENT_STATUS_MAPPING = {
    # From 0000 to 0099, 0400 and 0900
    "done": tuple(f"{i:04}" for i in range(100)) + ("0400", "0900"),
    "cancel": ("9915",),
    "error": tuple(ERROR_CODE_MAPPING),
}
