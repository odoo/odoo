# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.model
    def _prepare_transfer_account(self, name, company):
        res = super(WizardMultiChartsAccounts, self)._prepare_transfer_account(name, company)
        xml_id = self.env.ref('l10n_de.tag_de_asset_bs_B_III_2').id
        existing_tags = [x[-1:] for x in res.get('tag_ids', [])]
        res['tag_ids'] = [(6, 0, existing_tags + [xml_id])]
        return res

    # Write paperformat and report template used on company
    @api.model
    def execute(self):
        res = super(WizardMultiChartsAccounts, self).execute()
        if self.company_id.country_id.code == 'DE':
            self.company_id.write({'external_report_layout': 'din5008', 'paperformat_id': self.env.ref('l10n_de.paperformat_euro_din').id})
        return res

class Company(models.Model):
    _inherit = 'res.company'

    external_report_layout = fields.Selection(selection_add=[('din5008', 'Din 5008')])
