from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Real Estate Property Type"
    _order = "sequence, name"
    
    name = fields.Char(string="Name", required=True)
    
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Used to manually order types. Lower is better."
    )
    
    # One2many field for properties of this type
    property_ids = fields.One2many(
        "estate.property",
        "property_type_id",
        string="Properties"
    )
    
    # One2many field for offers of this type (inverse of property_type_id in offers)
    offer_ids = fields.One2many(
        "estate.property.offer",
        "property_type_id",
        string="Offers"
    )
    
    # Computed field for offer count
    offer_count = fields.Integer(
        string="Offers Count",
        compute="_compute_offer_count",
        store=True
    )
    
    # Computed method
    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)
    
    # SQL Constraints for uniqueness
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Property type name must be unique.'),
    ]