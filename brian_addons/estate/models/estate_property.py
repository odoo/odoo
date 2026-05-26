from odoo import fields, models
from dateutil.relativedelta import relativedelta


class EstatePropertyModel(models.Model):
    # Underscore: Model's internal identifier in Odoo
    # Defines the table name in the database
    # Required—every model needs one
    _name = 'estate_property_model'  # The model name itself
    _description = 'Model for Estate Property'

    # Char: represented as a Python unicode str and a SQL VARCHAR
    # estate_name = fields.Char('Estate Property Name', required=True, translate=True)
    # title = fields.Char()
    name = fields.Char(required=True)  # Reserved Field, Each property record has a name
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(default=lambda self: fields.Date.today() + relativedelta(months=3), copy=False)
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
        string='Type', selection=[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')]
    )

    # haha = fields.Char(string="Hahahehe this is a custom field name")

    # If a model has active, Odoo automatically hides records where active=False from searches/lists (unless you explicitly include them)
    active = fields.Boolean(default=True)  # Reserved Field names

    # Reserved field: lifecycle stages of the object, used by the states attribute on fields.
    state = fields.Selection(
        string='State',
        required=True,
        selection=[
            ('new', 'New'),
            ('offer_received', 'Offer Received'),
            ('offer_accepted', 'Offer Accepted'),
            ('sold', 'Sold'),
            ('cancelled', 'Cancelled'),
        ],
        copy=False,
        default='new',  # must use one of the values from selection, not label
    )


# - The name field is a Char which will be represented as a Python unicode str and a SQL VARCHAR.
# - Field names, by default, are generated automatically e.g. expected_price => Expected Price
