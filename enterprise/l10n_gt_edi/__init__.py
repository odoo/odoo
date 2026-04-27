from . import models
from . import wizard


def _l10n_gt_edi_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'gt'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_gt_edi_account_tax(),
            'account.fiscal.position': Template._get_gt_edi_account_fiscal_position(),
        })
