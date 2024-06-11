from odoo import _
from . import models
from . import tests


def _l10n_es_pos_post_init_hook(env):
    es_companies = env.companies.filtered(lambda c: c.chart_template and c.chart_template.startswith('es_'))
    for company in es_companies:
        pos_configs = env['pos.config'].search([
            *env['pos.config']._check_company_domain(company),
        ])
        income_account = env.ref(f'account.{company.id}_account_common_7000', raise_if_not_found=False)
        simplified_inv_journal = env['account.journal'].create({
            'type': 'sale',
            'name': _('Simplified Invoices'),
            'code': 'SINV',
            'default_account_id': income_account.id if income_account else False,
            'company_id': company.id,
            'sequence': 30,
        })
        pos_configs.l10n_es_simplified_invoice_journal_id = simplified_inv_journal
