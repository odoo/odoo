# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def _l10n_es_edi_verifactu_post_init_hook(env):
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        if company.chart_template.startswith("es_canary"):
            tax_data = {
                **Template._get_es_verifactu_account_tax_es_common(),
                **Template._get_es_verifactu_account_tax_es_canary_common(),
            }
        else:
            tax_data = {
                **Template._get_es_verifactu_account_tax_es_common(),
                **Template._get_es_verifactu_account_tax_es_common_mainland(),
            }
        Template._load_data({
            'account.tax': tax_data,
        })
