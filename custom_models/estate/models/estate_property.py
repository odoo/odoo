from dateutil.relativedelta import relativedelta

from odoo import fields, models


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "A test Model"

    name = fields.Char(string='Estate Name', required=True)
    description = fields.Text(string='Description')
    postcode = fields.Char(string='Postcode')
    date_availability = fields.Date(string='Data Available',
                                    default=lambda self: fields.Date.today() + relativedelta(months=+3),
                                    copy=False)
    expected_price = fields.Float(string='Expected Price', required=True)
    selling_price = fields.Float(string='Selling Price', readonly=True, copy=False)
    bedrooms = fields.Integer(string='Bedroom Count', default=3)
    living_area = fields.Integer(string='Living Area')
    facades = fields.Integer(string='Facades')
    garage = fields.Boolean(string='Has Garage')
    garden = fields.Boolean(string='Has Garden')
    garden_area = fields.Integer(string='Garden Area')
    garden_orientation = fields.Selection(
        string='Orientation',
        selection=[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')],
        help='Used to select the orientation of the garden.'
    )
    active = fields.Boolean(string="Active", default=True)
    state = fields.Selection(string='State', selection=[('new', 'New'), ('offer_received', 'Offer Received'),
                                                        ('offer_accepted', 'Offer Accepted'), ('sold', 'Sold'),
                                                        ('canceled', 'Canceled')], copy=False, required=True,
                             default='new')
