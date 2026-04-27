from odoo import api, fields, models


class AccountAssetCategory(models.Model):
    _name = 'l10n_ro_saft.account.asset.category'
    _description = "Asset categories for Romania's saft"
    _order = "code"
    _rec_names_search = ['code', 'description']

    _sql_constraints = [
        ('code_unique', 'unique (code)', 'The code of the asset category must be unique !'),
    ]

    description = fields.Char(string="Description", required=True, translate=True)
    code = fields.Char(string="Code", required=True)
    depreciation_min = fields.Integer(string="Minimum Depreciation")
    depreciation_max = fields.Integer(string="Maximum Depreciation")
    asset_ids = fields.One2many('account.asset', 'l10n_ro_saft_account_asset_category_id', string="Assets")

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for asset_category in self:
            asset_category.display_name = f'{asset_category.code} {asset_category.description}'
