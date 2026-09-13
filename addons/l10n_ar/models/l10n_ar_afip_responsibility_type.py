from odoo import fields, models


class L10n_ArAfipResponsibilityType(models.Model):
    _name = "l10n_ar.afip.responsibility.type"

    _description = "ARCA Responsibility Type"
    _order = "sequence"

    name = fields.Char(
        index="trigram",
        required=True,
    )
    sequence = fields.Integer()
    code = fields.Char(
        index=True,
        required=True,
    )
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint("unique(name)", "Name must be unique!")
    _code_uniq = models.Constraint("unique(code)", "Code must be unique!")
