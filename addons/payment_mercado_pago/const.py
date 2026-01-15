# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import LazyTranslate


_lt = LazyTranslate(__name__)

PROXY_URL = 'https://mercadopago.api.odoo.com/api/mercado_pago/1'

PAYMENT_RETURN_ROUTE = '/payment/mercado_pago/return'
OAUTH_RETURN_ROUTE = '/payment/mercado_pago/oauth/return'
WEBHOOK_ROUTE = '/payment/mercado_pago/webhook'


# The countries supported by Mercado Pago.
SUPPORTED_COUNTRIES = {
    'AR',
    'BO',
    'BR',
    'CL',
    'CO',
    'CR',
    'DO',
    'EC',
    'GT',
    'HN',
    'MX',
    'NI',
    'PA',
    'PY',
    'PE',
    'SV',
    'UY',
    'VE',
}

# Mapping of country codes to corresponding currency codes.
CURRENCY_MAPPING = {
    'AR': 'ARS',  # Argentina - Argentine Peso
    'BO': 'BOB',  # Bolivia - Boliviano
    'BR': 'BRL',  # Brazil - Brazilian Real
    'CL': 'CLP',  # Chile - Chilean Peso
    'CO': 'COP',  # Colombia - Colombian Peso
    'CR': 'CRC',  # Costa Rica - Costa Rican Colón
    'DO': 'DOP',  # Dominican Republic - Dominican Peso
    'EC': 'USD',  # Ecuador - United States Dollar
    'GT': 'GTQ',  # Guatemala - Guatemalan Quetzal
    'HN': 'HNL',  # Honduras - Honduran Lempira
    'MX': 'MXN',  # Mexico - Mexican Peso
    'NI': 'NIO',  # Nicaragua - Nicaraguan Córdoba
    'PA': 'PAB',  # Panama - Panamanian Balboa (also uses USD)
    'PY': 'PYG',  # Paraguay - Paraguayan Guaraní
    'PE': 'PEN',  # Peru - Peruvian Sol
    'SV': 'USD',  # El Salvador - United States Dollar
    'UY': 'UYU',  # Uruguay - Uruguayan Peso
    'VE': 'VES'   # Venezuela - Venezuelan Bolívar
}

# Set of currencies where Mercado Pago's minor units deviates from the ISO 4217 standard.
# See https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xls
# vs. https://api.mercadopago.com/currencies. Last seen online: 2024-10-29.
CURRENCY_DECIMALS = {
    'COP': 0,
    'HNL': 0,
    'NIO': 0,
}

# The codes of the payment methods to activate when Mercado Pago is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'amex',
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
}

# Mapping of payment method codes to Mercado Pago codes.
PAYMENT_METHODS_MAPPING = {
    'card': 'debit_card,credit_card,prepaid_card',
    'paypal': 'digital_wallet',
    'mastercard': 'master',
    'mercado_pago_wallet': 'mercado_pago',
}

# Mapping of transaction states to Mercado Pago payment statuses.
# See https://www.mercadopago.com.mx/developers/en/reference/payments/_payments_id/get.
TRANSACTION_STATUS_MAPPING = {
    'pending': ('pending', 'in_process', 'in_mediation', 'authorized'),
    'done': ('approved', 'refunded'),
    'canceled': ('cancelled', 'null'),
    'error': ('rejected',),
}

# Mapping of error states to Mercado Pago error messages.
# See https://www.mercadopago.com.ar/developers/en/docs/checkout-api/response-handling/collection-results
ERROR_MESSAGE_MAPPING = {
    'accredited': _lt(
        "Your payment has been credited. In your summary you will see the charge as a statement "
        "descriptor."
    ),
    'pending_contingency': _lt(
        "We are processing your payment. Don't worry, in less than 2 business days, we will notify "
        "you by e-mail if your payment has been credited."
    ),
    'pending_review_manual': _lt(
        "We are processing your payment. Don't worry, less than 2 business days we will notify you "
        "by e-mail if your payment has been credited or if we need more information."
    ),
    'cc_rejected_bad_filled_card_number': _lt("Check the card number."),
    'cc_rejected_bad_filled_date': _lt("Check expiration date."),
    'cc_rejected_bad_filled_other': _lt("Check the data."),
    'cc_rejected_bad_filled_security_code': _lt("Check the card security code."),
    'cc_rejected_blacklist': _lt("We were unable to process your payment, please use another card."),
    'cc_rejected_call_for_authorize': _lt("You must authorize the payment with this card."),
    'cc_rejected_card_disabled': _lt(
        "Call your card issuer to activate your card or use another payment method. The phone "
        "number is on the back of your card."
    ),
    'cc_rejected_card_error': _lt(
        "We were unable to process your payment, please check your card information."
    ),
    'cc_rejected_duplicated_payment': _lt(
        "You have already made a payment for that value. If you need to pay again, use another card"
        " or another payment method."
    ),
    'cc_rejected_high_risk': _lt(
        "We were unable to process your payment, please use another card."
    ),
    'cc_rejected_insufficient_amount': _lt("Your card has not enough funds."),
    'cc_rejected_invalid_installments': _lt(
        "This payment method does not process payments in installments."
    ),
    'cc_rejected_max_attempts': _lt(
        "You have reached the limit of allowed attempts. Choose another card or other means of "
        "payment."
    ),
    'cc_rejected_other_reason': _lt("Payment was not processed, use another card or contact issuer.")
}
