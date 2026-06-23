from odoo import api,models,fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare
from dateutil.relativedelta import relativedelta

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Properties"

    _inherit = ["mail.activity.mixin", "mail.thread"]

    name = fields.Char(required=True)
    description = fields.Text()
    date_availability = fields.Date(string="Available From", default= fields.Datetime.today() + relativedelta(months=3), copy=False)
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer()
    has_garden = fields.Boolean()
    garden_area = fields.Integer()
    total_area = fields.Integer(compute="_compute_total_area")
    property_type_id = fields.Many2one('estate.property.type', string="Property Type")
    buyer_id = fields.Many2one('res.partner')
    sales_person_id = fields.Many2one('res.users', string="Salesman", default=lambda self: self.env.user)
    offer_ids = fields.One2many("estate.property.offer","property_id")
    best_price = fields.Float(compute="_compute_best_price", string="Best Offer")
    tag_ids = fields.Many2many("estate.property.tag")
    state = fields.Selection(
        selection=[('new','New'),('offer_received','Offer Received'),('offer_accepted','Offer Accepted'),('sold','Sold'),
                   ('cancelled','Cancelled')], default="new", required = True 
    )

    @api.depends("living_area","garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.offer_ids.mapped("price"))
            else:
                record.best_price = 0.0

    
    def sell_property(self):
        for record in self:
            if record.state == 'cancelled':
                raise UserError("Cancelled properties cannot be sold")
            else:
                record.state = 'sold'


    def cancel_property(self):
        for record in self:
            if record.state == 'sold':
                raise UserError("Sold properties cannot be cancelled")
            else:
                record.state = 'cancelled'

    _check_expected_price = models.Constraint(
        'CHECK(expected_price > 0)',
        'The expected price must be strictly positive'
    )

    _check_selling_price = models.Constraint(
        'CHECK(selling_price >= 0)',
        'The selling price must be positive'
    )


    @api.constrains("expected_price","selling_price")
    def check_valid_selling_price(self):
        for record in self:
            if float_compare(record.selling_price,0.9*record.expected_price,precision_digits=2) < 0 and not float_is_zero(record.selling_price,precision_digits=2):
                raise ValidationError("Selling price cannot be less than 90% of the expected price")