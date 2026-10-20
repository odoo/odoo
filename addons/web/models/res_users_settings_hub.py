from odoo import fields, models


class ResUsersSettingsHub(models.Model):
    _name = 'res.users.settings.hub'
    _description = 'User Settings for Hub Actions'

    user_setting_id = fields.Many2one('res.users.settings', required=True, ondelete='cascade', index=True, export_string_translation=False)
    hub_id = fields.Many2one('ir.hub', required=True, ondelete='cascade', export_string_translation=False)
    res_id = fields.Integer(required=True, export_string_translation=False)
    # ordered ids of the items pinned by the user
    pinned_item_ids = fields.Json(export_string_translation=False)

    _res_users_settings_hub_unique = models.Constraint(
        'UNIQUE (user_setting_id, hub_id, res_id)',
        'The user should have one unique hub setting per hub and record id.',
    )
