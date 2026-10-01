from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_vehicle_account = fields.Boolean(
        string="Requires vehicle",
        help="Check this box if a vehicle has to be linked to the account, when creating a bill for an expense or when creating an asset.",
    )

    @api.onchange('account_type')
    def _onchange_account_type(self):
        res = super()._onchange_account_type()
        if self.is_vehicle_account and self.account_type not in ('asset_fixed', 'expense', 'expense_depreciation', 'expense_other', 'income_other'):
            self.is_vehicle_account = False
        return res
