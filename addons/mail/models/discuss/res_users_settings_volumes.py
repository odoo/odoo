# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.mail.tools.discuss import Store


class ResUsersSettingsVolumes(models.Model):
    """ Represents the volume of the sound that the user of user_setting_id will receive from partner_id. """
    _name = 'res.users.settings.volumes'
    _inherit = ["bus.listener.mixin", "bus.sync.mixin"]
    _description = 'User Settings Volumes'

    user_setting_id = fields.Many2one('res.users.settings', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', ondelete='cascade', index=True)
    guest_id = fields.Many2one('res.partner', ondelete='cascade', index=True)
    volume = fields.Float(default=0.5, help="Ranges between 0.0 and 1.0, scale depends on the browser implementation")

    _partner_unique = models.UniqueIndex("(user_setting_id, partner_id) WHERE partner_id IS NOT NULL")
    _guest_unique = models.UniqueIndex("(user_setting_id, guest_id) WHERE guest_id IS NOT NULL")
    _partner_or_guest_exists = models.Constraint(
        'CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))',
        'A volume setting must have a partner or a guest.',
    )

    @api.depends('user_setting_id', 'partner_id', 'guest_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.user_setting_id.user_id.name} - {rec.partner_id.name or rec.guest_id.name}'

    def _discuss_users_settings_volume_format(self):
        return [{
            'id': volume_setting.id,
            'volume': volume_setting.volume,
            "partner_id": {
                "id": volume_setting.partner_id.id,
                "name": volume_setting.partner_id.name,
            } if volume_setting.partner_id else None,
            "guest_id": {
                "id": volume_setting.guest_id.id,
                "name": volume_setting.guest_id.name,
            } if volume_setting.guest_id else None,
            'user_setting_id': {
                'id': volume_setting.user_setting_id.id,
            },
        } for volume_setting in self]

    def _bus_channels(self):
        return self.user_setting_id._bus_channels()

    def _store_volume_fields(self, res: Store.FieldList):
        res.attr("volume")
        res.one("partner_id", "_store_avatar_fields")
        res.one("guest_id", "_store_avatar_fields")
        res.one("user_setting_id", [])

    def _sync_field_names(self, res):
        super()._sync_field_names(res)
        self._store_volume_fields(res[None])
