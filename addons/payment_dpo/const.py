# Part of Odoo. See LICENSE file for full copyright and licensing details.

PAYMENT_STATUS_MAPPING = {
    'pending': ('003', '007'),
    'authorized': ('001', '005'),
    'done': ('000', '002'), # TODO-PDA verify the codes 002: Transaction overpaid/underpaid
    'cancel': ('900', '901', '902', '903', '904', '950'),
    'error': ('801', '802', '803', '804'),
}

# The codes of the payment methods to activate when DPO is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods
    'card',
    'mobile',
    'bank_transfer',
    'xpay',
    'paypal',
    # Brand payment methods
    'visa',
    'mastercard',
    'amex',
}

# Mapping of payment method codes to DPO codes.
PAYMENT_METHODS_MAPPING = {
    # default tab displayed in the payment page (primary payment methods)
    'card': 'CC',
    'paypal': 'PP',
    'bank_transfer': 'BT',
    # effective payment methods (brand payment methods)
    'dtb_tz': 'DTBTanzaniaTZS', #TODO-PDA adapt to the new method code
    'dtb_ke': 'DTBKenyaKES',
}
# TODO-PDA complete PAYMENT_METHODS_MAPPING and DEFAULT_PAYMENT_METHOD_CODES
# MO    Mobile (mobile apps) -> need to be a primary payment method (+ apps as brand payment methods)
# mobile apps: airtel money, mpesa (existing), mtn momo, orange money, tigo pesa, vodafone mpesa
# XP    xPay (pay later) -> new primary payment method to add
# SD Secure EFT, USSD (existing), QR code, online EFT
