# Part of Odoo. See LICENSE file for full copyright and licensing details.

def get_payment_option(payment_method_code):
    """ Map the payment method code to one of the payment options expected by APS.

    As APS expects the specific card brand (e.g, VISA) rather than the generic 'card' option, we
    skip the mapping and return an empty string when the provided payment method code is 'card'.
    This allows the user to select the desired brand on APS' checkout page.

    :param str payment_method_code: The code of the payment method.
    :return: The corresponding APS' payment option.
    :rtype: str
    """
    return payment_method_code.upper() if payment_method_code != 'card' else ''
