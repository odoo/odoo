# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.mail.tools.discuss import Store


class ResUsersSettings(models.Model):
    _name = "res.users.settings"
    _inherit = ["res.users.settings", "bus.sync.mixin"]

    volume_settings_ids = fields.One2many('res.users.settings.volumes', 'user_setting_id', string="Volumes of other partners")

    # Notifications
    channel_notifications = fields.Selection(
        [("all", "All Messages"), ("no_notif", "Nothing")],
        "Channel Notifications",
        help="This setting will only be applied to channels. Mentions only if not specified.",
    )

    def _store_settings_fields(self, res: Store.FieldList):
        """Fields to send to the store settings singleton. Modules override to add theirs."""
        res.extend(["channel_notifications"])
        res.many("volume_settings_ids", "_store_volume_fields")

    def _sync_field_names(self, res):
        super()._sync_field_names(res)
        self._store_settings_fields(res[None])

    @api.model
    def _get_fields_blacklist(self):
        return [*super()._get_fields_blacklist(), "volume_settings_ids"]

    def set_volume_setting(self, partner_id, volume, guest_id=None):
        """
        Saves the volume of a guest or a partner.
        Either partner_id or guest_id must be specified.
        :param float volume: the selected volume between 0 and 1
        :param int partner_id:
        :param int guest_id:
        """
        self.ensure_one()
        volume_setting = self.env['res.users.settings.volumes'].search([
            ('user_setting_id', '=', self.id), ('partner_id', '=', partner_id), ('guest_id', '=', guest_id)
        ])
        if volume_setting:
            volume_setting.volume = volume
        else:
            volume_setting = self.env['res.users.settings.volumes'].create({
                'user_setting_id': self.id,
                'volume': volume,
                'partner_id': partner_id,
                'guest_id': guest_id,
            })
            volume_setting._bus_send(
                "mail.record/insert",
                Store().add(volume_setting, "_store_volume_fields"),
            )
