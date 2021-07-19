from odoo import api, fields, models, _

class Product(models.Model):
    _inherit = "product.template"

    witholding_tax_ids = fields.Many2many('account.tax', 'product_wth_rel', 'prod_id', 'tax_id', help="Default witholding used when selling the product.", string='Customer Witholdings',
        domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.company.account_sale_tax_id)