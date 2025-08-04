# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def _l10n_es_edi_verifactu_post_init_hook(env):
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_es_verifactu_account_tax(),
        })
