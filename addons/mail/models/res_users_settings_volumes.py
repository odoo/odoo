# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsersSettingsVolumes(models.Model):
    """ Represents the volume of the sound that the user of user_setting_id will receive from partner_id. """
    _name = 'res.users.settings.volumes'
    _description = 'User Settings Volumes'

    user_setting_id = fields.Many2one('res.users.settings', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', ondelete='cascade', index=True)
    guest_id = fields.Many2one('res.partner', ondelete='cascade', index=True)
    volume = fields.Float(default=0.5, help="Ranges between 0.0 and 1.0, scale depends on the browser implementation")

    def init(self):
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS res_users_settings_volumes_partner_unique ON %s (user_setting_id, partner_id) WHERE partner_id IS NOT NULL" % self._table)
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS res_users_settings_volumes_guest_unique ON %s (user_setting_id, guest_id) WHERE guest_id IS NOT NULL" % self._table)

    _sql_constraints = [
        ("partner_or_guest_exists", "CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))", "A volume setting must have a partner or a guest."),
    ]

    def _discuss_users_settings_volume_format(self):
        return [{
            'id': volume_setting.id,
            'volume': volume_setting.volume,
            'guest_id': {
                'id': volume_setting.guest_id.id,
                'name': volume_setting.guest_id.name,
            } if volume_setting.guest_id else [('clear',)],
            'partner_id': {
                'id': volume_setting.partner_id.id,
                'name': volume_setting.partner_id.name,
            } if volume_setting.partner_id else [('clear',)],
            'user_setting_id': {
                'id': volume_setting.user_setting_id.id,
            },
        } for volume_setting in self]
