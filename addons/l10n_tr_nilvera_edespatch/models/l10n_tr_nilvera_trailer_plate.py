from odoo import fields, models


class L10nTrNilveraTrailerPlate(models.Model):
    _name = 'l10n_tr.nilvera.trailer.plate'
    _order = 'name'
    _description = "Trailer Plate numbers for Trailer containers in Turkiye"

    _sql_constraints = [
        ('name_unique', 'unique(name)', "Trailer plate number must be unique")
    ]

    name = fields.Char("Trailer Plate number")
