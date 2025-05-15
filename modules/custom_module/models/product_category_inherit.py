from odoo import models, fields, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    menupro_id = fields.Char(string='MenuPro ID')
    picture = fields.Char(string='Picture')
    type_name = fields.Char(string='Type Name')

    @api.model
    def create_from_api_data(self, category_data):
        """ Create or update POS categories from API data. """
        for data in category_data:
            category = self.search([('id', '=', data['id'])], limit=1)
            if category:
                category.write(data)
            else:
                self.create(data)