from odoo import fields, models

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate property"

    name = fields.Char("Title")
    description = fields.Html("Description")
    id = fields.Integer("ID")
    ref = fields.Char("Reference")
    create_uid = fields.Integer("Create ID")
    create_date = fields.Date("Create Date")
    date_availability = fields.Date("Available from")
    write_uid = fields.Integer("Write ID")
    property_Type = fields.Char("Property Type")
    postcode = fields.Char("Postcode")
    bedrooms = fields.Integer("Bedrooms", default=2)
    living_area = fields.Integer("Living Area(sqm)")
    facades = fields.Integer("Facades")
    garage = fields.Boolean("Garage")
    garden = fields.Boolean("Garden")
    garden_area = fields.Integer("Garden Area(sqm)")
    garden_orientation = fields.Selection(
        selection = [('North','North'),('South', 'South'),('East', 'East'),('West', 'West')],
        string= "Garden Orientation",
        required= True)
    state = fields.Selection([
        ('0', 'New'),
        ('1', 'Offer Received'),
        ('2', 'Offer Accepted'),
        ('3', 'Sold'),
        ('4', 'Canceled')], string="State", default="0", required=True)
    expected_price = fields.Float("Expected Price")
    selling_price = fields.Float("Selling Price", readonly=True)
    visit_id = fields.Many2one('estate.visit', string="Visit")

