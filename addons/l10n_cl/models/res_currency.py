from odoo import _, api, fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    l10n_cl_currency_code = fields.Char(
        string="Currency Code",
        translate=True,
    )
    l10n_cl_short_name = fields.Char(
        string="Short Name",
        translate=True,
    )
