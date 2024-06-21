from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    product_tmpl_id = fields.Many2one('product.template', 'Product Template')
    tiktok_logistic_id = fields.Char('Tiktok Logistic ID')