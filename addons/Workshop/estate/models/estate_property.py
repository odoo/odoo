from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Real Estate Properties"

    name = fields.Char(required=True)
    description = fields.Text()
    date_availability = fields.Date()
    expected_price = fields.Float()
    selling_price = fields.Float()
    bedrooms = fields.Integer()
    living_area = fields.Integer()
    has_garden = fields.Boolean()
    garden_area = fields.Integer()
    total_area = fields.Integer(compute = "_compute_total_area")
    property_type_id = fields.Many2one("estate.property.type", string="Property Type")
    buyer_id = fields.Many2one("res.partner", string = "Buyer")
    salesperson_id = fields.Many2one("res.users", string = "Real Estate Agent", default=lambda self: self.env.user)
    offer_ids = fields.One2many("estate.property.offer", "property_id")
    best_price = fields.Float(compute="_compute_best_price", string = "Best Price")
    state = fields.Selection(selection=[("new", "New"), ("offer_accepted", "Offer Accepted"), ("sold", "Sold"), 
                                        ("cancelled", "Cancelled")], default="new")
    
    tag_ids = fields.Many2many("estate.property.tag")

    _check_expected_price = models.Constraint("CHECK(expected_price > 0)", "The expected price must be strictly positive")

    _check_selling_price = models.Constraint("CHECK(selling_price>= 0)", "The selling price must be positive")

    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.offer_ids.mapped("price"))
            else:
                record.best_price = 0.0

    @api.depends("living_area", "garden_area", "has_garden")
    def _compute_total_area(self):
        for record in self:
            if record.has_garden:
                record.total_area = record.living_area + record.garden_area
            else:
                record.total_area = record.living_area

    def sell_property(self):
        for record in self:
            if record.state == "cancelled":
                raise UserError("cancelled properties cannot be sold")
            elif record.state == "new":
                raise UserError("Please accept an offer first")
            else:
                record.state = "sold"

    def cancel_property(self):
        for record in self:
            if record.state == "sold":
                raise UserError("sold properties cannot be cancelled")
            else:
                record.state = "cancelled"
    
    @api.constrains("expected_price", "selling_price")
    def _check_valid_selling_price(self):
        for record in self:
            if float_compare(record.selling_price, 0.9 * record.expected_price, precision_digits=2) < 0 and not float_is_zero(record.selling_price, precision_digits=2):
                raise ValidationError("Selling price must be at least 90 percent of the expected price")