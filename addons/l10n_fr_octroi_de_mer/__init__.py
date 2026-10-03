from . import models


def post_init_hook(env):
    for company in env['res.company'].search([('chart_template', '=like', 'fr%'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_fr_octroi_de_mer_taxes(),
            'account.tax.group': Template._get_fr_octroi_de_mer_tax_groups(),
        })
