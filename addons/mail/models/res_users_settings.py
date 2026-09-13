import typing

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .res_users_settings_volumes import ResUsersSettingsVolumes

_debug = DebugLog(__name__)


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    is_discuss_sidebar_category_channel_open = fields.Boolean(
        string="Is discuss sidebar category channel open?",
        default=True,
    )
    is_discuss_sidebar_category_chat_open = fields.Boolean(
        string="Is discuss sidebar category chat open?",
        default=True,
    )

    push_to_talk_key = fields.Char(
        string="Push-To-Talk shortcut",
        help="String formatted to represent a key with modifiers following this pattern: shift.ctrl.alt.key, e.g: truthy.1.true.b",
    )
    use_push_to_talk = fields.Boolean(
        string="Use the push to talk feature",
        default=False,
    )
    voice_active_duration = fields.Integer(
        string="Duration of voice activity in ms",
        default=200,
        help="How long the audio broadcast will remain active after passing the volume threshold",
    )
    volume_settings_ids: ResUsersSettingsVolumes = fields.One2many(
        comodel_name="res.users.settings.volumes",
        inverse_name="user_setting_id",
        string="Volumes of other partners",
    )

    channel_notifications = fields.Selection(
        selection=[("all", "All Messages"), ("no_notif", "Nothing")],
        help="This setting will only be applied to channels. Mentions only if not specified.",
    )

    @api.model
    def _format_settings(self, fields_to_format: list[str]) -> dict:
        res = super()._format_settings(fields_to_format)
        if "volume_settings_ids" in fields_to_format:
            volume_settings = (
                self.volume_settings_ids._discuss_users_settings_volume_format()
            )
            res.pop("volume_settings_ids", None)
            res["volumes"] = [("ADD", volume_settings)]
        return res

    def set_res_users_settings(self, new_settings: dict) -> dict:
        formatted = super().set_res_users_settings(new_settings)
        _debug.lifecycle(
            "settings_changed", settings=self.ids, fields=sorted(new_settings)
        )
        self._bus_send("res.users.settings", formatted)
        return formatted

    def set_volume_setting(
        self, partner_id: int, volume: float, guest_id: int | None = None
    ) -> None:
        self.check_singleton()
        volume_setting = self.env["res.users.settings.volumes"].search(
            [
                ("user_setting_id", "=", self.id),
                ("partner_id", "=", partner_id),
                ("guest_id", "=", guest_id),
            ]
        )
        _debug.lifecycle(
            "volume_set",
            settings=self.id,
            partner=partner_id,
            guest=guest_id,
            existing=bool(volume_setting),
        )
        if volume_setting:
            volume_setting.volume = volume
        else:
            volume_setting = self.env["res.users.settings.volumes"].create(
                {
                    "user_setting_id": self.id,
                    "volume": volume,
                    "partner_id": partner_id,
                    "guest_id": guest_id,
                }
            )
        self._bus_send(
            "res.users.settings.volumes",
            volume_setting._discuss_users_settings_volume_format(),
        )
