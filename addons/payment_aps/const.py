# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Mapping of transaction states to APS payment statuses.
# See https://paymentservices-reference.payfort.com/docs/api/build/index.html#transactions-response-codes.
PAYMENT_STATUS_MAPPING = {"pending": ("19",), "done": ("14",)}

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"benefit", "knet", "mada", "meeza", "naps", "omannet"}
