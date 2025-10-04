# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers


def _post_init_hook(env):
    # When installed, should create the luxury tax group with specific XML ID
    for company in env['res.company'].search([('chart_template', '=', 'id')]):
        ChartTemplate = env["account.chart.template"].with_company(company)
        if not ChartTemplate.ref("l10n_id_tax_group_luxury_goods", raise_if_not_found=False):
            ChartTemplate._load_data(
                {
                    "account.tax.group": {
                        "l10n_id_tax_group_luxury_goods": {
                            "name": "Luxury Good Taxes (ID)"
                        }
                    }
                }
            )
