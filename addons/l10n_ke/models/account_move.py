from odoo import models, fields
from odoo.addons import account


class AccountMove(account.AccountMove):

    l10n_ke_wh_certificate_number = fields.Char(
        string="Withholding Certificate Number",
        help="Customer withholding certificate number",
    )

    l10n_ke_wh_certificate_date = fields.Date(
        string="Date of Certificate",
    )
