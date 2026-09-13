from odoo import fields, models


class L10n_Eg_EdiActivityType(models.Model):
    _name = "l10n_eg_edi.activity.type"
    _description = "ETA code for activity type"
    _rec_name = "name"
    _rec_names_search = ["name", "code"]

    name = fields.Char(
        translate=True,
        required=True,
    )
    code = fields.Char(required=True)
