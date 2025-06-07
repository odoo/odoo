# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'hu')], order="parent_path"):
        # Apply default cash rounding configuration
        company._l10n_hu_edi_configure_company()

        # Set Hungarian fields on taxes
        env['account.chart.template'].with_company(company)._load_data({
            'account.tax': {
                xmlid: vals
                for xmlid, vals in env['account.chart.template']._get_hu_account_tax().items()
                if env['account.chart.template'].with_company(company).ref(xmlid, raise_if_not_found=False)
            }
        })
