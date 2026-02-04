from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
from datetime import datetime, timedelta

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Real Estate Property Offer"
    _order = "price desc"
    
    price = fields.Float(string="Price", required=True, digits=(12, 2))
    
    status = fields.Selection(
        string="Status",
        selection=[
            ('accepted', 'Accepted'),
            ('refused', 'Refused'),
        ],
        copy=False
    )
    
    validity = fields.Integer(string="Validity (days)", default=7)
    
    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline"
    )
    
    partner_id = fields.Many2one(
        "res.partner", 
        string="Partner", 
        required=True
    )
    
    property_id = fields.Many2one(
        "estate.property", 
        string="Property", 
        required=True
    )
    
    # Related field to property type
    property_type_id = fields.Many2one(
        "estate.property.type",
        string="Property Type",
        related="property_id.property_type_id",
        store=True,
        index=True
    )
    
    create_date = fields.Datetime(string="Created Date", readonly=True, default=lambda self: fields.Datetime.now())
    
    # Computed methods
    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                create_date = fields.Datetime.from_string(record.create_date)
                record.date_deadline = create_date + timedelta(days=record.validity)
            else:
                record.date_deadline = False
    
    def _inverse_date_deadline(self):
        for record in self:
            if record.create_date and record.date_deadline:
                create_date = fields.Datetime.from_string(record.create_date)
                deadline_date = fields.Datetime.from_string(record.date_deadline)
                record.validity = (deadline_date - create_date).days
            else:
                record.validity = 7
    
    # Action methods
    def action_accept(self):
        """Accept the offer"""
        for record in self:
            if record.property_id.state == 'sold':
                raise UserError("Cannot accept offer for a sold property.")
            
            # Check if there's already an accepted offer
            accepted_offers = self.env['estate.property.offer'].search([
                ('property_id', '=', record.property_id.id),
                ('status', '=', 'accepted'),
                ('id', '!=', record.id)
            ])
            
            if accepted_offers:
                raise UserError("Another offer has already been accepted for this property.")
            
            # Check if offer price is at least 90% of expected price
            expected_price = record.property_id.expected_price
            min_acceptable_price = expected_price * 0.9
            
            if float_compare(record.price, min_acceptable_price, precision_digits=2) < 0:
                raise ValidationError(
                    f"Cannot accept offer: The price ({record.price:.2f}) is lower than "
                    f"90% of the expected price ({min_acceptable_price:.2f})."
                )
            
            # Accept this offer
            record.status = 'accepted'
            
            # Update property
            record.property_id.write({
                'selling_price': record.price,
                'buyer_id': record.partner_id.id,
                'state': 'offer_accepted'
            })
        return True
    
    def action_refuse(self):
        """Refuse the offer"""
        for record in self:
            record.status = 'refused'
            
            # If this was the accepted offer, clear property selling info
            if record.status == 'accepted':
                record.property_id.write({
                    'selling_price': 0,
                    'buyer_id': False,
                    'state': 'offer_received' if record.property_id.offer_ids else 'new'
                })
        return True
    
    # Python Constraints
    @api.constrains('price')
    def _check_price(self):
        """Check that offer price is strictly positive"""
        for record in self:
            if float_compare(record.price, 0.0, precision_digits=2) <= 0:
                raise ValidationError("Offer price must be strictly positive.")
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create method to set property state and validate price
        
        Validates that:
        - Property is not sold
        - Offer price is not lower than existing offers
        """
        # Обрабатываем каждое значение в списке
        for vals in vals_list:
            # Получаем объект свойства
            if 'property_id' in vals:
                property_obj = self.env['estate.property'].browse(vals['property_id'])
                
                # Проверяем, что объект не продан
                if property_obj.state == 'sold':
                    raise UserError(
                        f"Cannot create an offer for a sold property ({property_obj.name})."
                    )
                
                # Проверяем, что цена не ниже существующих предложений
                if 'price' in vals:
                    existing_offers = self.env['estate.property.offer'].search([
                        ('property_id', '=', vals['property_id'])
                    ])
                    
                    if existing_offers:
                        # Находим максимальную цену из существующих предложений
                        max_existing_price = max(existing_offers.mapped('price'))
                        if float_compare(vals['price'], max_existing_price, precision_digits=2) < 0:
                            raise ValidationError(
                                f"Cannot create offer with price {vals['price']:.2f}. "
                                f"It is lower than the highest existing offer price of {max_existing_price:.2f}."
                            )
        
        # Создаем предложения через super()
        offers = super().create(vals_list)
        
        # Обновляем состояние свойств на 'offer_received'
        for offer in offers:
            if offer.property_id.state == 'new':
                offer.property_id.state = 'offer_received'
        
        return offers