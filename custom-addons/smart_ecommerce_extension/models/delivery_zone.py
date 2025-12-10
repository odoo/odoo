# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryZone(models.Model):
    _name = 'delivery.zone'
    _description = 'Delivery Zone'
    _order = 'sequence, name'

    name = fields.Char(
        string='Zone Name',
        required=True,
        help='e.g., "Nouakchott Urban", "Interior Regions"',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Cities covered
    city_ids = fields.Text(
        string='Cities',
        required=True,
        help='Comma-separated list of cities in this zone',
    )
    
    # Pricing
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    base_price = fields.Monetary(
        string='Base Price',
        currency_field='currency_id',
        required=True,
        help='Base delivery price for this zone',
    )
    extra_price_per_kg = fields.Monetary(
        string='Extra Price per Kg',
        currency_field='currency_id',
        default=0.0,
        help='Additional price per kilogram above base weight',
    )
    base_weight_kg = fields.Float(
        string='Base Weight (kg)',
        default=1.0,
        help='Weight included in base price',
    )
    
    # Delivery time
    estimated_days = fields.Integer(
        string='Estimated Days',
        default=3,
        help='Estimated delivery days for this zone',
    )
    min_delivery_days = fields.Integer(
        string='Min Delivery Days',
        default=2,
    )
    max_delivery_days = fields.Integer(
        string='Max Delivery Days',
        default=5,
    )
    
    # Restrictions
    max_weight_kg = fields.Float(
        string='Max Weight (kg)',
        default=30.0,
        help='Maximum deliverable weight for this zone',
    )
    free_delivery_threshold = fields.Monetary(
        string='Free Delivery Threshold',
        currency_field='currency_id',
        default=0.0,
        help='Order amount above which delivery is free (0 = no free delivery)',
    )

    @api.constrains('base_weight_kg', 'max_weight_kg')
    def _check_weights(self):
        for zone in self:
            if zone.base_weight_kg <= 0:
                raise ValidationError(_('Base weight must be positive.'))
            if zone.max_weight_kg < zone.base_weight_kg:
                raise ValidationError(_('Max weight must be greater than or equal to base weight.'))

    @api.constrains('min_delivery_days', 'max_delivery_days', 'estimated_days')
    def _check_delivery_days(self):
        for zone in self:
            if zone.min_delivery_days > zone.max_delivery_days:
                raise ValidationError(_('Min delivery days cannot exceed max delivery days.'))
            if not (zone.min_delivery_days <= zone.estimated_days <= zone.max_delivery_days):
                raise ValidationError(_('Estimated days must be between min and max delivery days.'))

    def get_cities_list(self):
        """Return list of cities in this zone"""
        self.ensure_one()
        if not self.city_ids:
            return []
        return [city.strip().lower() for city in self.city_ids.split(',') if city.strip()]

    def city_in_zone(self, city):
        """Check if a city is in this zone"""
        self.ensure_one()
        if not city:
            return False
        return city.strip().lower() in self.get_cities_list()

    def compute_delivery_price(self, weight_kg, order_total=0.0):
        """
        Compute delivery price based on weight.
        
        Args:
            weight_kg: Total weight in kilograms
            order_total: Order total for free delivery check
            
        Returns:
            float: Computed delivery price
        """
        self.ensure_one()
        
        # Check free delivery threshold
        if self.free_delivery_threshold > 0 and order_total >= self.free_delivery_threshold:
            return 0.0
        
        # Check max weight
        if weight_kg > self.max_weight_kg:
            raise ValidationError(
                _('Weight (%(weight)s kg) exceeds maximum for zone "%(zone)s" (%(max)s kg)') % {
                    'weight': weight_kg,
                    'zone': self.name,
                    'max': self.max_weight_kg,
                }
            )
        
        # Calculate price
        price = self.base_price
        
        extra_weight = weight_kg - self.base_weight_kg
        if extra_weight > 0:
            price += extra_weight * self.extra_price_per_kg
        
        return price

    def get_delivery_estimate(self):
        """Get formatted delivery estimate string"""
        self.ensure_one()
        if self.min_delivery_days == self.max_delivery_days:
            return _('%d days') % self.min_delivery_days
        return _('%d-%d days') % (self.min_delivery_days, self.max_delivery_days)

    @api.model
    def find_zone_for_city(self, city):
        """Find delivery zone that contains the given city"""
        if not city:
            return self.browse()
        
        zones = self.search([('active', '=', True)])
        for zone in zones:
            if zone.city_in_zone(city):
                return zone
        
        return self.browse()  # Return empty recordset if not found

    @api.model
    def get_all_cities(self):
        """Get list of all cities with delivery coverage"""
        zones = self.search([('active', '=', True)])
        cities = set()
        for zone in zones:
            cities.update(zone.get_cities_list())
        return sorted(list(cities))

