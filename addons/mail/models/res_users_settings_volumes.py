import typing

from odoo import api, fields, models

if typing.TYPE_CHECKING:
    from .discuss.mail_guest import MailGuest
    from .res_partner import ResPartner
    from odoo.addons.bus.models.res_users_settings import ResUsersSettings


class ResUsersSettingsVolumes(models.Model):
    _name = "res.users.settings.volumes"
    _description = "User Settings Volumes"

    user_setting_id: ResUsersSettings = fields.Many2one(
        comodel_name="res.users.settings",
        index=True,
        required=True,
        ondelete="cascade",
    )
    partner_id: ResPartner = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        ondelete="cascade",
    )
    guest_id: MailGuest = fields.Many2one(
        comodel_name="mail.guest",
        index=True,
        ondelete="cascade",
    )
    volume = fields.Float(
        default=0.5,
        help="Ranges between 0.0 and 1.0, scale depends on the browser implementation",
    )

    _partner_unique = models.UniqueIndex(
        "(user_setting_id, partner_id) WHERE partner_id IS NOT NULL"
    )
    _guest_unique = models.UniqueIndex(
        "(user_setting_id, guest_id) WHERE guest_id IS NOT NULL"
    )
    _partner_or_guest_exists = models.Constraint(
        "CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))",
        "A volume setting must have a partner or a guest.",
    )

    @api.depends("user_setting_id", "partner_id", "guest_id")
    def _compute_display_name(self) -> None:
        for rec in self:
            rec.display_name = f"{rec.user_setting_id.user_id.name} - {rec.partner_id.name or rec.guest_id.name}"

    def _discuss_users_settings_volume_format(self) -> list:
        return [
            {
                "id": volume_setting.id,
                "volume": volume_setting.volume,
                "partner_id": {
                    "id": volume_setting.partner_id.id,
                    "name": volume_setting.partner_id.name,
                }
                if volume_setting.partner_id
                else None,
                "guest_id": {
                    "id": volume_setting.guest_id.id,
                    "name": volume_setting.guest_id.name,
                }
                if volume_setting.guest_id
                else None,
                "user_setting_id": {
                    "id": volume_setting.user_setting_id.id,
                },
            }
            for volume_setting in self
        ]
