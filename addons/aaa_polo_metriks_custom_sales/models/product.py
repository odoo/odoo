from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    custom_price_1 = fields.Monetary(string="Prezzo 2")
    custom_price_2 = fields.Monetary(string="Prezzo 3")
