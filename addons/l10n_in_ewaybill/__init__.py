# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import demo
from . import wizard


def post_init_hook(env):
    for company in env['res.company'].search([('chart_template', '=', 'in')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        if ChartTemplate.ref('demo_invoice_b2b_1', raise_if_not_found=False):
            ChartTemplate._load_data({
                'res.company': ChartTemplate._l10n_in_ewaybill_res_company_demo(company.chart_template),
                'l10n.in.ewaybill': ChartTemplate._l10n_in_ewaybill_demo(company.chart_template),
            })
