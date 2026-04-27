from odoo import fields, models, api


class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'

    l10n_in_value_residual = fields.Monetary(
        string='Depreciable Value',
        help="New residual amount for the asset",
        compute="_compute_l10n_in_value_residual",
        store=True,
        readonly=False,
    )
    l10n_in_fiscal_code = fields.Char(related='company_id.account_fiscal_country_id.code')

    @api.depends('date')
    def _compute_l10n_in_value_residual(self):
        for record in self:
            if record.asset_id._check_degressive_special_asset():
                record.l10n_in_value_residual = record.asset_id._get_residual_value_at_date(record.date) - record.salvage_value
            record.value_residual = record.asset_id._get_residual_value_at_date(record.date)

    def _get_own_book_value(self):
        if not self.asset_id._check_degressive_special_asset():
            return super()._get_own_book_value()
        return self.l10n_in_value_residual + self.salvage_value

    def _get_new_asset_values(self, current_asset_book):
        self.ensure_one()
        if not self.asset_id._check_degressive_special_asset():
            return super()._get_new_asset_values(current_asset_book)
        old_l10n_in_value_residual = self.asset_id.l10n_in_value_residual
        return current_asset_book, min(current_asset_book - old_l10n_in_value_residual, self.salvage_value)

    def _get_increase_original_value(self, residual_increase, salvage_increase):
        if not self.asset_id._check_degressive_special_asset():
            return super()._get_increase_original_value(residual_increase, salvage_increase)
        return residual_increase

    def modify(self):
        if self.asset_id._check_degressive_special_asset():
            self.value_residual = self._get_own_book_value()
        return super().modify()
