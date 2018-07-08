# -*- coding: utf-8 -*-
from odoo import api, models, _


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.model
    def _prepare_transfer_account(self, name, company):
        res = super(WizardMultiChartsAccounts, self)._prepare_transfer_account(name, company)
        xml_id = self.env.ref('l10n_de.tag_de_asset_bs_B_III_2').id
        existing_tags = [x[-1:] for x in res.get('tag_ids', [])]
        res['tag_ids'] = [(6, 0, existing_tags + [xml_id])]
        return res
