from odoo import fields, models


class L10nTrNilveraTrailerPlate(models.Model):
    _name = 'l10n_tr.nilvera.trailer.plate'
    _order = 'name'
    _description = "GİB Plate numbers"

    _name_uniq = models.Constraint(
        'unique(name,plate_number_type)',
        "A Plate Number with that type already exists."
    )

    name = fields.Char(string="GİB Plate Number")
    plate_number_type = fields.Selection(
        string="Plate Number",
        selection=[
            ('vehicle', "Vehicle"),
            ('trailer', "Plate"),
        ],
        required=True,
    )
