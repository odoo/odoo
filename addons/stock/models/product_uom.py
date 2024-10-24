# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class ProductUom(models.Model):
    _description = 'Link between the products and the UoM'

    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True, ondelete='cascade')
    name = fields.Char('Barcode')
