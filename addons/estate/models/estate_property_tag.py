from odoo import models, fields

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Real Estate Property Tag"
    _order = "name asc"
    
    # Champs
    name = fields.Char(required=True)
    color = fields.Char(string="Color")
    
    
    # Contraintes SQL    
    _sql_constraints = [
        ('unique_tag_name', 'UNIQUE(name)', 'The tag name must be unique.')
    ]
