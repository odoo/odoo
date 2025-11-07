from . import controllers
from . import demo
from . import models
from . import wizard


def _post_init_hook(env):
    env['res.groups']._activate_group_account_secured()

    for company in env['res.company'].search([('chart_template', '=', 'pt')], order="parent_path"):
        env['account.chart.template']._l10n_pt_load_certification_tax_data(company)
