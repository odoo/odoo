# type: ignore
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Real Estate Property'
    _order = 'id desc'

    # Champs de base
    name = fields.Char(string='Title', default="Name", required=True)
    description = fields.Text(compute="_compute_description")
    postcode = fields.Char()
    date_availability = fields.Date(string='Available From', default=fields.Date.today(), copy=False)
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(string='Selling Price', readonly=True, copy=False)
    bedrooms = fields.Integer()
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    total_area = fields.Integer(string="Total Area", compute="_compute_total_area")
    amount = fields.Float()
    garden_orientation = fields.Selection(
        selection=[
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West')
        ],
        help="Orientation of the garden"
    )
    active = fields.Boolean(string="Active", default=True)

    # États du bien immobilier
    state = fields.Selection([
        ('new', 'New'),
        ('offer_received', 'Offer Received'),
        ('offer_accepted', 'Offer Accepted'),
        ('sold', 'Sold'),
        ('cancelled', 'Cancelled')
    ], string="State", required=True, default='new', copy=False)

    # Contraintes SQL
    _sql_constraints = [
        ('check_expected_price_positive', 'CHECK(expected_price > 0)', 'The expected price must be strictly positive.'),
        ('check_selling_price_positive', 'CHECK(selling_price >= 0)', 'The selling price must be positive.'),
    ]

    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        for record in self:
            if not float_is_zero(record.selling_price, precision_digits=2) and \
               float_compare(record.selling_price, record.expected_price * 0.9, precision_digits=2) < 0:
                raise models.ValidationError("The selling price must be at least 90% of the expected price.")

    # Relations
    partner_id = fields.Many2one('res.partner', string="Partner")
    property_type_id = fields.Many2one('estate.property.type', string="Property Type")
    salesperson_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    buyer_id = fields.Many2one('res.partner', string='Buyer', copy=False)
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")

    # Meilleure offre
    best_price = fields.Float(string="Best Offer", compute="_compute_best_price", store=True)

    # Méthodes de calcul
    @api.depends('partner_id.name')
    def _compute_description(self):
        for record in self:
            if record.partner_id:
                record.description = f"Property owned by {record.partner_id.name}"
            else:
                record.description = "No partner linked"

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = (record.living_area or 0) + (record.garden_area or 0)

    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for property in self:
            prices = property.offer_ids.mapped("price")
            property.best_price = max(prices) if prices else 0.0

    # Réactions au changement
    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False

    # Actions sur les états
    def action_cancel(self):
        for record in self:
            if record.state == 'sold':
                raise UserError("You cannot cancel a property that has already been sold")
            record.state = 'cancelled'

    def action_sold(self):
        for record in self:
            if record.state == 'cancelled':
                raise UserError("You cannot sell a property that has already been cancelled")
            record.state = 'sold'

    # Suppression conditionnelle
    def unlink(self):
        for record in self:
            if record.state not in ['new', 'cancelled']:
                raise UserError("You cannot delete a property that is not in a draft or cancelled state")
        return super().unlink()
