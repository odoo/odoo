# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _


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
    'accredited': _(
        "Your payment has been credited. In your summary you will see the charge as a statement "
        "descriptor."
    ),
    'pending_contingency': _(
        "We are processing your payment. Don't worry, in less than 2 business days, we will notify "
        "you by e-mail if your payment has been credited."
    ),
    'pending_review_manual': _(
        "We are processing your payment. Don't worry, less than 2 business days we will notify you "
        "by e-mail if your payment has been credited or if we need more information."
    ),
    'cc_rejected_bad_filled_card_number': _("Check the card number."),
    'cc_rejected_bad_filled_date': _("Check expiration date."),
    'cc_rejected_bad_filled_other': _("Check the data."),
    'cc_rejected_bad_filled_security_code': _("Check the card security code."),
    'cc_rejected_blacklist': _("We were unable to process your payment, please use another card."),
    'cc_rejected_call_for_authorize': _("You must authorize the payment with this card."),
    'cc_rejected_card_disabled': _(
        "Call your card issuer to activate your card or use another payment method. The phone "
        "number is on the back of your card."
    ),
    'cc_rejected_card_error': _(
        "We were unable to process your payment, please check your card information."
    ),
    'cc_rejected_duplicated_payment': _(
        "You have already made a payment for that value. If you need to pay again, use another card"
        " or another payment method."
    ),
    'cc_rejected_high_risk': _(
        "We were unable to process your payment, please use another card."
    ),
    'cc_rejected_insufficient_amount': _("Your card has not enough funds."),
    'cc_rejected_invalid_installments': _(
        "This payment method does not process payments in installments."
    ),
    'cc_rejected_max_attempts': _(
        "You have reached the limit of allowed attempts. Choose another card or other means of "
        "payment."
    ),
    'cc_rejected_other_reason': _("Payment was not processed, use another card or contact issuer.")
}
