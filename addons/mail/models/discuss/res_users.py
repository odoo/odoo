from typing import Literal, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.discuss import Store

_debug = DebugLog(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    is_in_call = fields.Boolean(
        related="partner_id.is_in_call",
        string="Is in call",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        users = super().create(vals_list)
        users._subscribe_to_group_restricted_channels()
        return users

    def write(self, vals: ValuesType) -> Literal[True]:
        res = super().write(vals)
        if "active" in vals and not vals["active"]:
            self._unsubscribe_from_non_public_channels()
        if "group_ids" in vals:
            self._subscribe_to_group_restricted_channels()
        return res

    def unlink(self) -> Literal[True]:
        self._unsubscribe_from_non_public_channels()
        return super().unlink()

    def _subscribe_to_group_restricted_channels(self) -> None:
        if not self.all_group_ids:
            return
        channels = self.env["discuss.channel"].search(
            [("group_ids", "in", self.all_group_ids.ids)]
        )
        _debug.lifecycle(
            "group_channels_subscribed",
            users=self.ids,
            groups=len(self.all_group_ids),
            channels=len(channels),
        )
        channels._subscribe_users_automatically(partners=self.partner_id)

    def _unsubscribe_from_non_public_channels(self) -> None:
        members = (
            self.env["discuss.channel.member"]
            .sudo()
            .search(
                [
                    ("partner_id", "in", self.partner_id.ids),
                    ("channel_id.channel_type", "=", "channel"),
                    ("channel_id.group_public_id", "!=", False),
                ]
            )
        )
        _debug.lifecycle(
            "non_public_channels_unsubscribed", users=self.ids, members=len(members)
        )
        members.unlink()

    def _init_messaging(self, store: Store) -> None:
        user = self.with_user(self)
        channels = user.env["discuss.channel"]._get_channels_as_member()
        domain = [("channel_id", "in", channels.ids), ("is_self", "=", True)]
        members = user.env["discuss.channel.member"].search(domain)
        members_with_unread = members.filtered(
            lambda member: member.message_unread_counter
        )
        _debug.pipeline(
            "init_messaging",
            user=self.id,
            channels=len(channels),
            unread=len(members_with_unread),
        )
        super()._init_messaging(store)
        store.add_global_values(initChannelsUnreadCounter=len(members_with_unread))

    def _init_store_data(self, store: Store) -> None:
        super()._init_store_data(store)
        Credential = self.env["credential.credential"]
        store.add_global_values(
            hasGifPickerFeature=Credential._has_system_secret("discuss.klipy_api_key"),
            hasMessageTranslationFeature=Credential._has_system_secret(
                "mail.google_translate_api_key"
            ),
            hasCannedResponses=bool(
                self.env["mail.canned.response"]
                .sudo()
                .search(
                    [
                        "|",
                        ("create_uid", "=", self.env.user.id),
                        ("group_ids", "in", self.env.user.all_group_ids.ids),
                    ],
                    limit=1,
                )
            )
            if self.env.user
            else False,
            channel_types_with_seen_infos=sorted(
                self.env["discuss.channel"]._types_allowing_seen_infos()
            ),
        )
