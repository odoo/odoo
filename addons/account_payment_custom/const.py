# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__, default_lang="en_US")

REPORT_REASONS_MAPPING = {
    "unavailable_for_invoices": _lt("Not available for invoices")
}
