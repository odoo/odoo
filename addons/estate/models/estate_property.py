# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Real Estate Property'
    _order = 'id desc'

    name = fields.Char(required=True)
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
    garden_orientation = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West'),
    ])
    active = fields.Boolean(default=True)
    property_type_id = fields.Many2one('estate.property.type')
    partner_id = fields.Many2one('res.partner', string='Buyer', copy=False)
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    tag_ids = fields.Many2many('estate.property.tag')
    offer_ids = fields.One2many('estate.property.offer', 'property_id')
    total_area = fields.Integer(compute='_compute_total_area')
    best_price = fields.Float(compute='_compute_best_price')
    state = fields.Selection([
        ('new', 'New'),
        ('offer_received', 'Offer Received'),
        ('offer_accepted', 'Offer Accepted'),
        ('sold', 'Sold'),
        ('cancelled', 'Cancelled'),
    ], required=True, default='new', copy=False)

    _check_expected_price = models.Constraint('CHECK(expected_price > 0)', 'Expected price must be positive.')
    _check_selling_price = models.Constraint('CHECK(selling_price >= 0)', 'Selling price cannot be negative.')

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for property_record in self:
            property_record.total_area = property_record.living_area + property_record.garden_area

    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        for property_record in self:
            property_record.best_price = max(property_record.offer_ids.mapped('price'), default=0.0)

    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price_ratio(self):
        for property_record in self:
            if not float_is_zero(property_record.selling_price, precision_digits=2) and float_compare(
                property_record.selling_price, property_record.expected_price * 0.9, precision_digits=2,
            ) < 0:
                raise ValidationError(self.env._('The selling price must be at least 90% of the expected price.'))

    @api.onchange('garden')
    def _onchange_garden(self):
        for property_record in self:
            property_record.garden_area = 10 if property_record.garden else 0
            property_record.garden_orientation = 'north' if property_record.garden else False

    @api.ondelete(at_uninstall=False)
    def _unlink_except_new_or_cancelled(self):
        if any(property_record.state not in ('new', 'cancelled') for property_record in self):
            raise UserError(self.env._('Only new or cancelled properties can be deleted.'))

    def action_sold(self):
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(self.env._('A cancelled property cannot be sold.'))
        self.state = 'sold'
        return True

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'sold':
            raise UserError(self.env._('A sold property cannot be cancelled.'))
        self.state = 'cancelled'
        return True
