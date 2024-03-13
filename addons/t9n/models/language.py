from odoo import fields, models


class Language(models.Model):
    _name = "t9n.language"
    _description = "Language"

    name = fields.Char("Formal Name", required=True)
    code = fields.Char("Code", required=True)
    native_name = fields.Char("Native Name")
    direction = fields.Selection(
        required=True,
        selection=[
            ("ltr", "left-to-right"),
            ("rtl", "right-to-left"),
        ],
    )

    _sql_constraints = [
        ("language_code_unique", "unique(code)", "The language code must be unique.")
    ]
