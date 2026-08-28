from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__, default_lang="en_US")

# Reasons this module adds to the availability report built by `payment`. Kept
# separate from `payment.const.REPORT_REASONS_MAPPING` because the criterion is
# ours: `payment` knows nothing about pricelists.
REPORT_REASONS_MAPPING = {
    "pricelist_not_allowed": _lt("pricelist not allowed"),
}
