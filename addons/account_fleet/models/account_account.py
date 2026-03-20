from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_vehicle_account = fields.Boolean(
        string="Requires vehicle",
        help="Check this box if a vehicle has to be linked to the account, when creating a bill for an expense or when creating an asset.",
    )
