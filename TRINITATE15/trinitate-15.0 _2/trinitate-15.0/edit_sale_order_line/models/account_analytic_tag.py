from odoo import fields, models

class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"
    
    code = fields.Integer()
    product_tag = fields.Many2many(comodel_name="product.product.tag")  # nueva linea por isai
    name = fields.Char(required=True)  #  nueva linea por isai

