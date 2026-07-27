from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    oauth_token_ids = fields.One2many(string="OAuth Tokens", comodel_name='oauth.token', inverse_name='user_id')
