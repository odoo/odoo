from . import models
from . import wizards


def _post_init_hook(env):
    """Add the withholding tax groups and taxes to the companies already running the Georgian chart."""
    for company in env['res.company'].search([('chart_template', '=', 'ge'), ('parent_id', '=', False)]):
        template = env['account.chart.template'].with_company(company)
        template._load_data({'account.tax.group': template._get_ge_withholding_account_tax_group()})
        template._load_data({'account.tax': template._get_ge_withholding_account_tax()})
