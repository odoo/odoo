from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


# Used when Bancontact returns no error code (e.g. 429 and 503) or an undocumented one
DEFAULT_ERROR = _lt("Bancontact couldn't process the request. Please try again later.")

# ----- Payment API (authenticated with the API key of the product) ----- #
PAYMENT_API_ERRORS = {
    "UNAUTHORIZED": _lt("Bancontact rejected the API key. Please check the API key of the Bancontact product."),
    "ACCESS_DENIED": _lt("Bancontact denied the access to this API key. Please check the API key of the Bancontact product."),
    "TECHNICAL_ERROR": _lt("Bancontact encountered a technical error. Please try again later."),
}

CREATE_PAYMENT_ERRORS = {
    **PAYMENT_API_ERRORS,
    "BODY_MISSING": _lt("Bancontact rejected the payment request. Please try again or contact support."),
    "FIELD_IS_REQUIRED": _lt("Bancontact rejected the payment request. Please try again or contact support."),
    "FIELD_IS_INVALID": _lt("Bancontact rejected the payment request. Please try again or contact support."),
    "MERCHANT_PROFILE_NOT_FOUND": _lt("Bancontact doesn't know this product. Please check the Product ID of the Bancontact product."),
    "UNABLE_TO_PAY_CREDITOR": _lt("Bancontact can't accept payments for this product at the moment. Please contact Bancontact support."),
    "TRY_AGAIN_LATER": _lt("Bancontact is currently unavailable. Please try again later."),
}

CANCEL_PAYMENT_ERRORS = {
    **PAYMENT_API_ERRORS,
    "CALLER_NOT_ALLOWED_TO_CANCEL": _lt("This payment wasn't created with this Bancontact product, so it can't be cancelled with it."),
    "PAYMENT_NOT_FOUND": _lt("Bancontact doesn't know this payment."),
    "PAYMENT_NOT_PENDING": _lt("This payment can't be cancelled anymore: it's no longer pending."),
}

# ----- Refund API (authenticated with the signature of the company) ----- #
REFUND_API_ERRORS = {
    "VALIDATION_ERROR": _lt("Bancontact rejected the refund request. Please try again or contact support."),
    "UNAUTHORIZED": _lt("Bancontact couldn't verify the signature of the request. Please check that the JWKS URL of the Point of Sale settings is registered on the Bancontact Pro Portal."),
    "ACCESS_DENIED": _lt("Bancontact doesn't allow refunds for this Merchant ID. Please check the Bancontact Merchant ID in the Point of Sale settings."),
    "TECHNICAL_ERROR": _lt("Bancontact encountered a technical error. Please try again later."),
}

CREATE_REFUND_ERRORS = {
    **REFUND_API_ERRORS,
    "PAYMENT_FOR_REFUND_NOT_FOUND": _lt("Bancontact doesn't know the payment to refund."),
    "INVALID_REFUND_AMOUNT": _lt("The refund amount is higher than the amount left to refund on this payment."),
    "REFUND_NOT_ALLOWED": _lt("Refunds are not activated for this Bancontact product. Ask Bancontact support to activate them."),
    "REFUND_NOT_POSSIBLE": _lt("This payment can't be refunded at the moment. Please try again later."),
    "REFUND_REQUEST_CONFLICT": _lt("This refund was already sent to Bancontact with different details."),
}

FETCH_REFUND_ERRORS = {
    **REFUND_API_ERRORS,
    "PAYMENT_NOT_FOUND": _lt("Bancontact doesn't know the refunded payment."),
    "REFUND_NOT_FOUND": _lt("Bancontact doesn't know this refund."),
}
