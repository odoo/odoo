from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    is_tiktok_partner = fields.Boolean('Tiktok Partner', default=False)
    tiktok_username = fields.Char('Tiktok Username')