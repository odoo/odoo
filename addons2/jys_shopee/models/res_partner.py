from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    is_shopee_partner = fields.Boolean('Shopee Partner', default=False)
    shopee_username = fields.Char('Shopee Username')