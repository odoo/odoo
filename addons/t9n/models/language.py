from odoo import fields, models


class Language(models.Model):
    _name = "t9n.language"
    _description = "Language"

    name = fields.Char("Formal Name", required=True, readonly=True)
    code = fields.Char("Code", required=True, readonly=True)
    native_name = fields.Char("Native Name", readonly=True)
    direction = fields.Selection(
        required=True,
        selection=[
            ("ltr", "left-to-right"),
            ("rtl", "right-to-left"),
        ],
        readonly=True,
    )

    _sql_constraints = [
        ("language_code_unique", "unique(code)", "The language code must be unique.")
    ]
