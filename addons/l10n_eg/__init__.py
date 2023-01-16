from odoo import api, SUPERUSER_ID
from . import models


def load_translations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_eg.egypt_chart_template_standard').process_coa_translations()
