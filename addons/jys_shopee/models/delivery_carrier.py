from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    product_tmpl_id = fields.Many2one('product.template', 'Product Template')
    shopee_logistic_id = fields.Integer('Shopee Logistic ID')
    is_cashless = fields.Boolean('Cashless', default=False)