# -*- coding: utf-8 -*-
from odoo.addons import account

from odoo import models


class AccountChartTemplate(models.AbstractModel, account.AccountChartTemplate):

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'nl':
            company.account_journal_suspense_account_id.tag_ids += self.env.ref('l10n_nl.account_tag_25')
            company.get_unaffected_earnings_account().tag_ids += self.env.ref('l10n_nl.account_tag_12')
