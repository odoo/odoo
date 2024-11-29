# -*- coding: utf-8 -*-

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'nl':
            if cash_tag := self.env.ref('l10n_nl.account_tag_25', raise_if_not_found=False):
                company.account_journal_suspense_account_id.tag_ids += cash_tag
                company.transfer_account_id.tag_ids += cash_tag
            if undist_profit_tag := self.env.ref('l10n_nl.account_tag_undist_profit', raise_if_not_found=False):
                company.get_unaffected_earnings_account().tag_ids += undist_profit_tag
