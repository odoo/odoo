from odoo import _
from . import models
from . import tests


def _l10n_es_pos_post_init_hook(env):
    es_companies = env.companies.filtered(lambda c: c.chart_template and c.chart_template.startswith('es_'))
    for company in es_companies:
        pos_configs = env['pos.config'].search([
            *env['pos.config']._check_company_domain(company),
        ])
        pos_configs.setup_defaults(company)
