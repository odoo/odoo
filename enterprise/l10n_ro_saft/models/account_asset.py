from odoo import api, fields, models


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    l10n_ro_saft_account_asset_category_id = fields.Many2one('l10n_ro_saft.account.asset.category', string="Asset Category")
    l10n_ro_saft_account_asset_category_warning = fields.Boolean(
        string="Warning on account asset category",
        compute="_compute_l10n_ro_saft_account_asset_category_warning",
    )

    @api.depends('method_period', 'method_number', 'l10n_ro_saft_account_asset_category_id')
    def _compute_l10n_ro_saft_account_asset_category_warning(self):
        if self.l10n_ro_saft_account_asset_category_id:
            dep_min = self.l10n_ro_saft_account_asset_category_id.depreciation_min
            dep_max = self.l10n_ro_saft_account_asset_category_id.depreciation_max
            current_dep_in_year = int(self.method_period) / 12 * self.method_number
            self.l10n_ro_saft_account_asset_category_warning = current_dep_in_year < dep_min or current_dep_in_year > dep_max
        else:
            self.l10n_ro_saft_account_asset_category_warning = False
