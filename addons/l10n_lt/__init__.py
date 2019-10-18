from odoo import api, SUPERUSER_ID


def load_translations(cr, registry):
    """Load template translations."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref(
        'l10n_lt.account_chart_template_lithuania').process_coa_translations()
