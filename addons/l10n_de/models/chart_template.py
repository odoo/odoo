# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_transfer_account_for_direct_creation(self, name, company):
        res = super(AccountChartTemplate, self)._prepare_transfer_account_for_direct_creation(name, company)
        xml_id = self.env.ref('l10n_de.tag_de_asset_bs_B_III_2').id
        existing_tags = [x[-1:] for x in res.get('tag_ids', [])]
        res['tag_ids'] = [(6, 0, existing_tags + [xml_id])]
        return res

    # Write paperformat and report template used on company
    def load_for_current_company(self, sale_tax_rate, purchase_tax_rate):
        res = super(AccountChartTemplate, self).load_for_current_company(sale_tax_rate, purchase_tax_rate)
        company = self.env.user.company_id
        if company.country_id.code == 'DE':
            company.write({'external_report_layout': self.env.ref('l10n_de.external_layout_din5008').id,
            'paperformat_id': self.env.ref('l10n_de.paperformat_euro_din').id})
        return res
