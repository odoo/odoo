from . import demo
from . import models
from . import wizard


def _post_init_hook(env):
    env['res.groups']._activate_group_account_secured()

    group_user = env.ref('base.group_user', raise_if_not_found=False)
    group_sale_receipts = env.ref('account.group_sale_receipts', raise_if_not_found=False)
    if group_user and group_sale_receipts:
        group_user.sudo()._apply_group(group_sale_receipts)

    for company in env['res.company'].search([('chart_template', '=', 'pt')], order="parent_path"):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_pt_certification_account_tax(),
            'account.tax.group': Template._get_pt_certification_account_tax_group(),
        })
