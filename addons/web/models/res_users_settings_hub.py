from odoo import api, fields, models


class ResUsersSettingsHub(models.Model):
    _name = 'res.users.settings.hub'
    _description = 'User Settings for Hub Actions'

    user_setting_id = fields.Many2one('res.users.settings', required=True, ondelete='cascade', index=True, export_string_translation=False)
    hub_id = fields.Many2one('ir.actions.hub', required=True, ondelete='cascade', export_string_translation=False)
    res_id = fields.Integer(required=True, export_string_translation=False)
    # ordered ids of the items pinned by the user
    pinned_item_ids = fields.Json(export_string_translation=False)

    _res_users_settings_hub_unique = models.Constraint(
        'UNIQUE (user_setting_id, hub_id, res_id)',
        'The user should have one unique hub setting per hub and record id.',
    )

    @api.model
    def _get_pinned_items(self, hub, res_id):
        """ Return the items of ``hub`` pinned by the current user for the
        record ``res_id``, in display order.
        """
        setting = self.search([
            ('user_setting_id.user_id', '=', self.env.uid),
            ('hub_id', '=', hub.id),
            ('res_id', '=', res_id),
        ], limit=1)
        items = hub.sudo().item_ids
        # ignore the ids of deleted items
        return items.browse([
            item_id for item_id in setting.pinned_item_ids or [] if item_id in items.ids
        ])
