# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_transfer_account_for_direct_creation(self, name, company):
        res = super(AccountChartTemplate, self)._prepare_transfer_account_for_direct_creation(name, company)
        if company.account_fiscal_country_id.code == 'DE':
            xml_id = self.env.ref('l10n_de.tag_de_asset_bs_B_III_2').id
            res.setdefault('tag_ids', [])
            res['tag_ids'].append((4, xml_id))
        return res

    # Write paperformat and report template used on company
    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        if company.account_fiscal_country_id.code == 'DE':
            company.write({'external_report_layout_id': self.env.ref('l10n_de.external_layout_din5008').id,
            'paperformat_id': self.env.ref('l10n_de.paperformat_euro_din').id})
        return res
