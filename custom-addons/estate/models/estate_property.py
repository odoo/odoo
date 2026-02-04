from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
from datetime import datetime, timedelta

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Real Estate Property"
    _order = "id desc"
    
    # Basic fields
    name = fields.Char(string="Title", required=True, index=True)
    description = fields.Text(string="Description")
    postcode = fields.Char(string="Postcode")
    
    # Date fields
    date_availability = fields.Date(
        string="Available From", 
        copy=False,
        default=lambda self: fields.Date.today() + timedelta(days=90),
        index=True
    )
    
    # Price fields
    expected_price = fields.Float(
        string="Expected Price", 
        required=True,
        digits=(12, 2)
    )
    
    selling_price = fields.Float(
        string="Selling Price", 
        readonly=True,
        copy=False,
        digits=(12, 2),
        default=0.00
    )
    
    # Computed price field
    best_price = fields.Float(
        string="Best Offer",
        compute="_compute_best_price",
        digits=(12, 2),
        help="Best offer received"
    )
    
    # Property features
    bedrooms = fields.Integer(string="Bedrooms", default=4)
    living_area = fields.Integer(string="Living Area (sqm)", default=250)
    facades = fields.Integer(string="Facades", default=4)
    garage = fields.Boolean(string="Garage", default=False)
    garden = fields.Boolean(string="Garden", default=False)
    garden_area = fields.Integer(string="Garden Area (sqm)", default=1500)
    
    # Computed area field
    total_area = fields.Integer(
        string="Total Area (sqm)",
        compute="_compute_total_area"
    )
    
   
    # Garden orientation
    garden_orientation = fields.Selection(
        string="Garden Orientation",
        selection=[
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West'),
        ],
        help="Orientation of the garden",
        default='north'
    )
    
    # Status fields
    active = fields.Boolean(
        string="Active",
        default=True,
        index=True,
        help="Archive the property instead of deleting it"
    )
    
    state = fields.Selection(
        string="Status",
        selection=[
            ('new', 'New'),
            ('offer_received', 'Offer Received'),
            ('offer_accepted', 'Offer Accepted'),
            ('sold', 'Sold'),
            ('cancelled', 'Cancelled'),
        ],
        required=True,
        copy=False,
        default='new',
        index=True
    )
    
    # Many2one fields
    property_type_id = fields.Many2one(
        "estate.property.type", 
        string="Property Type"
    )
    
    buyer_id = fields.Many2one(
        "res.partner", 
        string="Buyer",
        copy=False
    )
    
    salesperson_id = fields.Many2one(
        "res.users", 
        string="Salesperson",
        default=lambda self: self.env.user
    )
    
    # Multi-company field
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Company that owns this property"
    )
    
    # Many2many field for tags
    tag_ids = fields.Many2many(
        "estate.property.tag",
        string="Tags"
    )
    
    # One2many field for offers
    offer_ids = fields.One2many(
        "estate.property.offer",
        "property_id",
        string="Offers"
    )
    
    # Computed methods
    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area
    
    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.offer_ids.mapped('price'))
            else:
                record.best_price = 0.0
    
    
    # Onchange methods
    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False
    
    # Action methods
    def action_sold(self):
        """Mark property as sold
        
        Validates that:
        - Property is not cancelled
        - Property has at least one accepted offer
        """
        for record in self:
            if record.state == 'cancelled':
                raise UserError("Cancelled properties cannot be sold.")
            
            # Check if there is at least one accepted offer
            accepted_offers = record.offer_ids.filtered(lambda o: o.status == 'accepted')
            if not accepted_offers:
                raise UserError("Cannot sell a property without an accepted offer.")
            
            record.state = 'sold'
        return True
    
    def action_cancel(self):
        """Cancel the property"""
        for record in self:
            if record.state == 'sold':
                raise UserError("Sold properties cannot be cancelled.")
            record.state = 'cancelled'
        return True
    
    # Python Constraints
    @api.constrains('expected_price')
    def _check_expected_price(self):
        """Check that expected price is strictly positive"""
        for record in self:
            if float_compare(record.expected_price, 0.0, precision_digits=2) <= 0:
                raise ValidationError("Expected price must be strictly positive.")
    
    @api.constrains('selling_price')
    def _check_selling_price(self):
        """Check that selling price is positive"""
        for record in self:
            if float_compare(record.selling_price, 0.0, precision_digits=2) < 0:
                raise ValidationError("Selling price must be positive.")
    
    @api.constrains('expected_price', 'selling_price')
    def _check_selling_price_percentage(self):
        """
        Check that selling price is not lower than 90% of expected price
        Only check when selling price is not zero (i.e., when an offer has been accepted)
        """
        for record in self:
            # Skip check if selling price is zero (no offer accepted yet)
            if float_is_zero(record.selling_price, precision_digits=2):
                continue
            
            # Calculate 90% of expected price
            min_acceptable_price = record.expected_price * 0.9
            
            # Compare selling price with 90% of expected price
            if float_compare(record.selling_price, min_acceptable_price, precision_digits=2) < 0:
                raise ValidationError(
                    f"The selling price cannot be lower than 90% of the expected price.\n"
                    f"Expected price: {record.expected_price:.2f}\n"
                    f"Minimum acceptable (90%): {min_acceptable_price:.2f}\n"
                    f"Selling price: {record.selling_price:.2f}"
                )
    
    # del  'new' or 'cancelled'
    @api.ondelete(at_uninstall=False)
    def _check_state_before_unlink(self):
        """Prevent deletion of properties that are not new or cancelled"""
        for record in self:
            if record.state not in ['new', 'cancelled']:
                raise UserError(
                    f"Cannot delete property '{record.name}' with state '{record.state}'. "
                    "Only properties with state 'New' or 'Cancelled' can be deleted."
                )
    # Method for toggling active status
    def action_toggle_active(self):
        """Toggle active status"""
        for record in self:
            record.active = not record.active