# -*- coding: utf-8 -*-
from . import models, wizard


def _l10n_sa_edi_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'sa'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        tax_data = Template._get_sa_edi_account_tax()

        tax_data = {
            xmlid: values
            for xmlid, values in tax_data.items()
            if Template.ref(xmlid, raise_if_not_found=False)
        }
        # Update existing taxes only
        if tax_data:
            Template._load_data({
                'account.tax': tax_data,
            })
