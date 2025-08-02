from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    embedded_actions_config = fields.Json(export_string_translation=False)
