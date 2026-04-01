# -*- coding: utf-8 -*-
from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('de_skr03', 'res.company')
    @template('de_skr04', 'res.company')
    def _get_de_res_company(self):
        return {
            self.env.company.id: {
                'external_report_layout_id': 'l10n_din5008.external_layout_din5008',
                'paperformat_id': 'l10n_din5008.paperformat_euro_din',
                'restrictive_audit_trail': True,
            }
        }

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        super()._setup_utility_bank_accounts(template_code, company, template_data)
        if template_code in ["de_skr03", "de_skr04"]:
            company.account_journal_suspense_account_id.tag_ids = self.env.ref('l10n_de.tag_de_asset_bs_B_II_4')
            company.transfer_account_id.tag_ids = self.env.ref('l10n_de.tag_de_asset_bs_B_IV')
