# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__, default_lang="en_US")

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"pay_on_invoice", "wire_transfer"}

# The key used in payment.data payloads to confirm custom transactions
CUSTOM_STATE_DONE_KEY = "confirmed"

REPORT_REASONS_MAPPING = {
    "pay_on_invoice_excluded_on_invoices": _lt("Pay on Invoice not available on Invoice documents")
}
