# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Mapping of transaction states to DPO payment statuses.
# See https://docs.dpopay.com/api/index.html#tag/Basic-Transaction-Operations/operation/verifyToken
PAYMENT_STATUS_MAPPING = {
    "pending": ("003", "007"),
    "authorized": ("001", "005"),
    "done": ("000", "002"),
    "cancel": ("900", "901", "902", "903", "904", "950"),
    "error": ("801", "802", "803", "804"),
}

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"card", "mobile"}

# Mapping of payment method codes to DPO codes
PAYMENT_METHODS_MAPPING = {"card": "CC", "mobile": "MO"}
