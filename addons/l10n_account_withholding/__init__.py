# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards


def _l10n_account_withholding_post_init(env):
    """ For existing companies with a chart template that is not from argentina """
    ar_template_codes = ['ar_ri', 'ar_ex', 'ar_base']
    companies = env['res.company'].search([('chart_template', 'not in', ar_template_codes)], order="parent_path")
    used_template_codes = set(companies.mapped('chart_template'))
    for template_code in used_template_codes:
        template_data = env['account.chart.template']._get_chart_template_data(template_code).pop('template_data')
        for company in companies.filtered(lambda c: c.chart_template == template_code):
            if company.parent_id or company.l10n_account_withholding_tax_base_account_id:
                continue

            code_digits = int(template_data.get('code_digits', 6))
            company.l10n_account_withholding_tax_base_account_id = env['account.account']._load_records([{
                'xml_id': f"account.{company.id}_l10n_account_withholding_tax_base_account_id",
                'values': {
                    'name': env._("WHT BASE AMOUNT"),
                    'prefix': '998',
                    'code_digits': code_digits,
                    'account_type': 'asset_current',
                    'reconcile': True,
                },
                'noupdate': True,
            }])
