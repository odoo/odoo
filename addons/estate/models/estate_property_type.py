from odoo import fields, models, api


class EstatePropertyType(models.Model):
    _name = 'estate.property.type'
    _description = 'Estate Property Type'
    _order = 'sequence, name asc'

    # Champs de base
    name = fields.Char(required=True)
    sequence = fields.Integer(string="Sequence")

    # Contraintes SQL
    _sql_constraints = [
        ('unique_type_name', 'UNIQUE(name)',
         'The property type name must be unique.')
    ]

    # Relations
    property_ids = fields.One2many(
        'estate.property',
        'property_type_id',
        string="Properties"
    )

    offer_ids = fields.One2many(
        'estate.property.offer',
        'property_type_id',
        string="Offers"
    )

    offer_count = fields.Integer(
        string="Number of Offers",
        compute="_compute_offer_count"
    )

    # Méthodes de calcul
    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)
