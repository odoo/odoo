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
    'mobile': 'MO',
    'bank_transfer': 'BT',
    'xpay': 'XP',
    'paypal': 'PP',
    # effective payment methods (brand payment methods)
    'visa': 'VISA',
    'mastercard': 'MASC',
    'amex': 'AMEX',
    'bank_transfer_ke_eur': 'DTBKenyaEUR',
    'bank_transfer_ke_zar': 'DTBKenyaZAR',
    'bank_transfer_tz_tzs': 'DTBTanzaniaTZS',
    # TODO-PDA add mobile payment methods + others allowed
}
