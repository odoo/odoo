# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def _l10n_es_edi_verifactu_post_init_hook(env):
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        # Filter out data for non-exsting taxes; else this function will raise.
        # In case of data for a non-existing tax we would try to create that tax.
        # This would fail because we don't supply enough information in this module (just `l10n_es_applicability`).
        tax_data = {
            xmlid: value
            for xmlid, value in Template._get_es_verifactu_account_tax().items()
            if Template.ref(xmlid, raise_if_not_found=False)
        }
        Template._load_data({
            'account.tax': tax_data,
        })
