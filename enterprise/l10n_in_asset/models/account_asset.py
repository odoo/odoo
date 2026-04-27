from odoo import api, fields, models


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    l10n_in_value_residual = fields.Monetary(
        compute='_compute_l10n_in_value_residual',
        export_string_translation=False,
    )

    @api.depends('value_residual', 'salvage_value', 'already_depreciated_amount_import')
    def _compute_l10n_in_value_residual(self):
        for record in self:
            if record._check_degressive_special_asset():
                record.l10n_in_value_residual = record.value_residual - record.salvage_value
            else:
                record.l10n_in_value_residual = record.value_residual

    def _degressive_linear_amount(self, residual_amount, degressive_amount, linear_amount):
        if not self._check_degressive_special_asset():
            return super()._degressive_linear_amount(residual_amount, degressive_amount, linear_amount)
        if abs(residual_amount) - abs(degressive_amount) < abs(self.salvage_value):
            degressive_amount = residual_amount - self.salvage_value
        return degressive_amount

    def _compute_total_depreciable_value(self):
        l10n_in_records = self.filtered(
            lambda asset: (
                asset._check_degressive_special_asset()
            )
        )
        for asset in l10n_in_records:
            asset.total_depreciable_value = asset.original_value
        super(AccountAsset, (self - l10n_in_records))._compute_total_depreciable_value()

    @api.constrains('depreciation_move_ids')
    def _check_depreciations(self):
        l10n_in_records = self.filtered(lambda asset: asset._check_degressive_special_asset())
        super(AccountAsset, (self - l10n_in_records))._check_depreciations()

    def _compute_value_residual(self):
        super()._compute_value_residual()
        for record in self.filtered(lambda asset: asset._check_degressive_special_asset()):
            record.value_residual += record.salvage_value

    def _compute_book_value(self):
        super()._compute_book_value()
        for record in self.filtered(lambda asset: asset._check_degressive_special_asset()):
            if not (record.state == 'close' and all(move.state == 'posted' for move in record.depreciation_move_ids)):
                record.book_value -= record.salvage_value

    def _get_own_book_value(self, date=None):
        self.ensure_one()
        if not self._check_degressive_special_asset():
            return super()._get_own_book_value(date)
        return self.value_residual

    def _get_depreciation_amount_end_of_lifetime(self, residual_amount, amount, days_until_period_end):
        if not self._check_degressive_special_asset():
            return super()._get_depreciation_amount_end_of_lifetime(residual_amount, amount, days_until_period_end)
        # To ensure reaching the salvage value at the end of the lifeTime
        if days_until_period_end >= self.asset_lifetime_days:
            amount = residual_amount - self.salvage_value
        return amount

    def _check_degressive_special_asset(self):
        return self.company_id.account_fiscal_country_id.code == 'IN' and self.method == 'degressive'
