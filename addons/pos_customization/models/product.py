from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    alternative_name = fields.Char(
        string='Alternative Product Name',
        help='An alternative name for the product to display in POS, takes priority over the original name.'
    )

    pos_alternative_product_ids = fields.Many2many(
        comodel_name='product.product',
        relation='product_template_pos_alternative_rel',
        column1='product_id',
        column2='alternative_id',
        string='POS Alternative Products',
        help='Alternative products to suggest in the POS for this product.',
        domain="[('available_in_pos', '=', True),('categ_id', '=', categ_id)]",
    )

    @api.constrains('alternative_name')
    def _check_unique_alternative_name(self):
        for record in self:
            if record.alternative_name:
                existing_name = self.env['product.template'].search_count([
                    ('alternative_name', '=', record.alternative_name),
                    ('id', '!=', record.id)
                ])
                if existing_name:
                    raise ValidationError("alternative_name must be unique")
                
    
class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        fields_to_add = [ 'public_description','alternative_name', 'pos_alternative_product_ids']
        result.extend(field for field in fields_to_add if field not in result)
        return result
