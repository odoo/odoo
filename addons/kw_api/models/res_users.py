import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = 'res.users'

    kw_api_token_ids = fields.One2many(
        comodel_name='kw.api.token', string='API token',
        inverse_name='user_id', )
