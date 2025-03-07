from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_description = fields.Text(
        string = 'Pos Description',
        help = 'Pos specific description'
    )
    
class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if 'pos_description' not in result:
            result.append('pos_description')
        return result
