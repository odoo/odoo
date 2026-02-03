from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Real Estate Property Tag"
    _order = "name"
    
    name = fields.Char(string="Name", required=True)
    color = fields.Integer(string="Color", default=0)
    
    # SQL Constraints for uniqueness
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Tag name must be unique.'),
    ]
    
    # Python constraint for better error handling
    @api.constrains('name')
    def _check_name_unique(self):
        for record in self:
            if self.search_count([('name', '=ilike', record.name), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"Tag with name '{record.name}' already exists.")