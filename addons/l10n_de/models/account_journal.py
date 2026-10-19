# -*- coding: utf-8 -*-

from odoo import api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        res = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'DE':
            tag_ids = res.get('tag_ids', [])
            tag_ids.append((4, self.env.ref('l10n_de.tag_de_asset_bs_B_IV').id))
            res['tag_ids'] = tag_ids

        return res
