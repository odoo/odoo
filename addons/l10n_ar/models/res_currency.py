from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    l10n_ar_afip_code = fields.Char(
        string="ARCA Code",
        size=4,
        help="This code will be used on electronic invoice",
    )
