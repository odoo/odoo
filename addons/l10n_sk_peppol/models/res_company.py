from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    peppol_validation_token = fields.Char(
        groups="account.group_account_manager",
        help="Verification token used to authenticate the user.",
    )
