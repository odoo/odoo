from odoo import models, fields ,api

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "adding type,salesman and partner to the main Module"
    _order = "sequence, name"

    sequence = fields.Integer('Sequence', default=1, help="Used to order types of the property. Lower is better.")

    name = fields.Char(
        required = True
    )

    number = fields.Integer(
        default = 0
    )


    property_ids= fields.One2many(
         "estate.property",
        "property_type_id"
    )

    _sql_constraints = [
        ('UniqueType','UNIQUE(name)','Anther type with same name')
    ]

