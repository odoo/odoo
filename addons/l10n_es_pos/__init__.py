from . import models


def _l10n_es_pos_post_init_hook(env):
    es_companies = env.companies.filtered(lambda c: c.chart_template and c.chart_template.startswith('es_'))
    for company in es_companies:
        pos_configs = env['pos.config'].search([
            *env['pos.config']._check_company_domain(company),
        ])
        for pos in pos_configs:
            pos._ensure_sinv_journal()
