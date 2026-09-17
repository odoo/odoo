from odoo import fields, models


class L10n_GeWhtCategory(models.Model):
    _name = 'l10n_ge.wht.category'
    _description = "Georgian Withholding Tax Category"
    _rec_name = 'l10n_ge_name'
    _rec_names_search = ('l10n_ge_name', 'l10n_ge_code')

    l10n_ge_code = fields.Char(
        string="RS.ge ID",
        required=True,
        help="Reference of the category in the RS.ge withholding tax return.",
    )
    l10n_ge_name = fields.Char(
        string="Description",
        required=True,
        translate=True,
        help="Income recipient category, as named in the RS.ge withholding tax return.",
    )
