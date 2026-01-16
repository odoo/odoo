from . import models
from . import wizard


def post_init(env):
    # Loading new field 'l10n_hr_tax_category_id' for existing Croatian taxes
    for company in env['res.company'].search([('chart_template', '=', 'hr')], order="parent_path"):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': {
                xmlid: vals
                for xmlid, vals in Template._get_hr_edi_account_tax().items()
                if Template.ref(xmlid, raise_if_not_found=False)
            }
        })
