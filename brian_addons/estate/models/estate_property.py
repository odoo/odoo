from odoo import fields, models

class EstatePropertyModel(models.Model):
    _name = 'estate_property_model'
    _description = 'Model for Estate Property'

    # Char: represented as a Python unicode str and a SQL VARCHAR
    # estate_name = fields.Char('Estate Property Name', required=True, translate=True)
    # title = fields.Char()
    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date()
    expected_price = fields.Float(required=True)
    selling_price = fields.Float()
    bedrooms = fields.Integer()
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
        string='Type',
        selection=[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')]
    )




