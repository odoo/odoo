# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        # EXTENDS account to creates a default account for this company when installing a chart template, to be used on tax-base lines.
        super()._setup_utility_bank_accounts(template_code, company, template_data)
        if template_code in {'ar_ri', 'ar_ex', 'ar_base'}:
            return

        self._setup_withholding_tax_base_account(company, template_data)

    @api.model
    def _setup_withholding_tax_base_account(self, company, template_data):
        if company.parent_id or company.withholding_tax_base_account_id:
            return

        code_digits = int(template_data.get('code_digits', 6))
        company.withholding_tax_base_account_id = self.env['account.account']._load_records([{
            'xml_id': f"account.{company.id}_withholding_tax_base_account_id",
            'values': {
                'name': self.env._("WHT BASE AMOUNT"),
                'prefix': '998',
                'code_digits': code_digits,
                'account_type': 'asset_current',
                'reconcile': False,
                'company_ids': [Command.link(company.id)],
            },
            'noupdate': True,
        }])
