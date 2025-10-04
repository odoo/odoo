from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_description = fields.Text(
        string='Pos Description',
        help='Pos specific description'
     )
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

    _sql_constraints = [
        (
            'unique_alternative_name',
            'UNIQUE(alternative_name)',
            'The Alternative Name must be unique across all products.'
        )                
    ]

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    @api.model
    def _load_pos_data_fields(self, config_id):
      fields_to_add = [ 'pos_description','alternative_name', 'pos_alternative_product_ids']
      parent_fields  = super()._load_pos_data_fields(config_id)
      parent_fields.extend(fields_to_add)
      return parent_fields
