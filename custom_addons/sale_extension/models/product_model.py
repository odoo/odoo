from odoo import fields, models


class ProductModel(models.Model):
    _inherit = "product.template"


    item_model = fields.Text(
        string='Modelo',
        readOnly=False,
        store=True,
        help='Modelo del producto a crear',
        default=""
    )