from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    menupro_id = fields.Char(string='MenuPro ID')

    @api.model_create_multi
    def create(self, vals_list):
        products = super(ProductProduct, self).create(vals_list)

        for product, vals in zip(products, vals_list):
            product_tmpl_id = vals.get('product_tmpl_id')
            if product_tmpl_id:
                product_tmpl = self.env['product.template'].sudo().browse(product_tmpl_id)
                product.menupro_id = product_tmpl.menupro_id
        return products
