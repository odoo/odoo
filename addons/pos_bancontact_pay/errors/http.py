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
