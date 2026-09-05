from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    oauth_token_ids = fields.One2many('oauth.token', 'user_id')
    manual_api_key_ids = fields.One2many(
        'res.users.apikeys', compute='_compute_manual_api_key_ids',
    )

    @api.depends('api_key_ids.oauth_token_id')
    def _compute_manual_api_key_ids(self):
        for user in self:
            user.manual_api_key_ids = user.api_key_ids.filtered(lambda api_key: not api_key.oauth_token_id)
