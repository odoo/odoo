from odoo import api, SUPERUSER_ID

def load_translations(cr, registry):
    """Load template translations."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref(
        'l10n_lv.account_chart_template_latvia').process_coa_translations()
        
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
