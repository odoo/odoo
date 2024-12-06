# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        """ We need to define a default account for use in community, while when enterprise is installed it's up to the user or l10n to define them. """
        super()._setup_utility_bank_accounts(template_code, company, template_data)
        if company.parent_id or template_code in {'ar_ri', 'ar_ex', 'ar_base'} or company.l10n_account_withholding_tax_base_account_id:
            return

        code_digits = int(template_data.get('code_digits', 6))
        company.l10n_account_withholding_tax_base_account_id = self.env['account.account']._load_records([{
            'xml_id': f"account.{company.id}_l10n_account_withholding_tax_base_account_id",
            'values': {
                'name': _("WHT BASE AMOUNT"),
                'prefix': '998',
                'code_digits': code_digits,
                'account_type': 'asset_current',
                'reconcile': True,
            },
            'noupdate': True,
        }])
