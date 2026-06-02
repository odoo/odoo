from odoo import fields, models, api
from dateutil.relativedelta import relativedelta


class EstatePropertyModel(models.Model):
    # Underscore: Model's internal identifier in Odoo
    # Defines the table name in the database
    # Required—every model needs one
    _name = 'estate.property'  # The model name itself
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

    # Computed field
    show_all = fields.Boolean(
        string='Show all',
        compute='_compute_show_all',
        store=True,  # must set so it can be used in xml
    )

    # depends on the field it reads data field
    @api.depends('active')
    def _compute_show_all(self):
        for record in self:
            record.show_all = True

    # Many2one fields: other records connect to 1 estate
    property_type = fields.Many2one('estate.property.type')

    # res.partner and res.users are built-in Odoo models
    # self.env: gives access to request parameters
    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        index=True,  # database index on the column, making searches/filters on that field faster
        default=lambda self: self.env.user,  # defers execution until a new record is actually being created
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Buyer',
        index=True,
    )

    tag_ids = fields.Many2many('estate.property.tag', string='Tags')

    # comodel is the offer model, inverse field is property_id
    # - estate.property.offer: comodel (the "many" side)
    # - property_id: the Many2one field on that comodel, must match the field name on offer model
    offer_ids = fields.One2many('estate.property.offer', 'property_id', string="Offers")
