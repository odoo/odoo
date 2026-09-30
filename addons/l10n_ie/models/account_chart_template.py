from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'ie':
            if cash_tag := self.env.ref('l10n_ie.l10n_ie_account_tag_cash_bank_hand', raise_if_not_found=False):
                company.account_journal_suspense_account_id.tag_ids += cash_tag
                company.transfer_account_id.tag_ids += cash_tag
