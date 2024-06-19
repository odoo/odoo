from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    is_tiktok = fields.Boolean('TikTok Invoice')