import typing
import uuid
from datetime import datetime, timedelta
from typing import Literal, Self

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import Request, request
from odoo.libs.datetime import all_timezones
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq, get_lang

from odoo.addons.base.models.res_partner import _selection_timezones
from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput

if typing.TYPE_CHECKING:
    from ..mail_presence import MailPresence
    from .discuss_channel import DiscussChannel
    from odoo.addons.base.models.res_country import ResCountry

_debug = DebugLog(__name__)


class MailGuest(models.Model):
    _name = "mail.guest"
    _description = "Guest"
    _inherit = ["mixin.avatar", "mixin.mail.presence", "mixin.bus.listener"]
    _avatar_name_field = "name"
    _cookie_name = "dgid"
    _cookie_separator = "|"

    @api.model
    def _selection_langs(self) -> list[tuple[str, str]]:
        return self.env["res.lang"].get_installed()

    name = fields.Char(required=True)
    access_token = fields.Char(
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        readonly=True,
        required=True,
        groups="base.group_system",
    )
    country_id: ResCountry = fields.Many2one(comodel_name="res.country")
    email = fields.Char()
    lang = fields.Selection(
        selection=_selection_langs,
        string="Language",
    )
    timezone = fields.Selection(selection=_selection_timezones)
    channel_ids: DiscussChannel = fields.Many2many(
        comodel_name="discuss.channel",
        relation="discuss_channel_member",
        column1="guest_id",
        column2="channel_id",
        string="Channels",
        copy=False,
    )
    presence_ids: MailPresence = fields.One2many(
        comodel_name="mail.presence",
        inverse_name="guest_id",
        groups="base.group_system",
    )

    @api.depends("presence_ids.status")
    def _compute_presence(self) -> None:
        for guest in self:
            guest.im_status = guest.presence_ids.status or "offline"
            guest.offline_since = (
                guest.presence_ids.last_poll if guest.im_status == "offline" else None
            )

    def _get_guest_from_token(self, token: str = "") -> Self:
        guest = self.env["mail.guest"]
        parts = token.split(self._cookie_separator)
        if len(parts) == 2:
            guest_id, guest_access_token = parts
            if not guest_id.isdigit():
                return guest
            guest = self.browse(int(guest_id)).sudo().exists()
            if (
                not guest
                or not guest.access_token
                or not consteq(guest.access_token, guest_access_token)
            ):
                _debug.logic("guest_token_rejected", guest=int(guest_id))
                guest = self.env["mail.guest"]
        return guest.sudo(False)

    def _get_guest_from_context(self) -> Self:
        guest = self.env.context.get("guest")
        if isinstance(guest, self.pool["mail.guest"]):
            assert len(guest) <= 1, "Context guest should be empty or a single record."
            return guest.sudo(False).with_context(guest=guest)
        return self.env["mail.guest"]

    def _get_or_create_guest(
        self, *, guest_name: str, country_code: str | None, timezone: str | None
    ) -> Self:
        if not (guest := self._get_guest_from_context()):
            guest = self.create(
                {
                    "country_id": self.env["res.country"]
                    .search([("code", "=", country_code)])
                    .id,
                    "lang": get_lang(self.env).code,
                    "name": guest_name,
                    "timezone": timezone,
                }
            )
            _debug.lifecycle(
                "guest_created",
                guest=guest.id,
                country=country_code,
                timezone=timezone,
                lang=guest.lang,
            )
            guest._set_auth_cookie()
        return guest.sudo(False)

    def _get_timezone_from_request(self, request: Request) -> str | Literal[False]:
        timezone = request.cookies.get("tz")
        return timezone if timezone in all_timezones() else False

    def _update_name(self, name: str) -> None:
        self.check_singleton()
        name = name.strip()
        if len(name) < 1:
            raise UserError(_("Guest's name cannot be empty."))
        if len(name) > 512:
            raise UserError(_("Guest's name is too long."))
        self.name = name
        _debug.lifecycle("guest_renamed", guest=self.id, channels=len(self.channel_ids))
        payload = Store(bus_channel=self).add(self, ["avatar_128", "name"]).get_result()
        if payload:
            targets = self.channel_ids
            for target in (targets, self):
                if target:
                    target._bus_send("mail.record/insert", payload)

    def _update_timezone(self, timezone: str) -> None:
        self.check_singleton()
        query = """
            UPDATE mail_guest
            SET timezone = %s
            WHERE id IN (
                SELECT id FROM mail_guest WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (timezone, self.id))
        _debug.lifecycle(
            "guest_timezone",
            guest=self.id,
            timezone=timezone,
            updated=self.env.cr.rowcount,
        )
        self.invalidate_recordset(["timezone"])

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return ["avatar_128", "im_status", "name"]

    def _set_auth_cookie(self) -> None:
        self.check_singleton()
        expiration_date = datetime.now() + timedelta(days=365)
        request.future_response.set_cookie(
            self._cookie_name,
            self._format_auth_cookie(),
            httponly=True,
            expires=expiration_date,
        )
        request.update_context(guest=self.sudo(False))

    def _format_auth_cookie(self) -> str:
        self.check_singleton()
        return f"{self.id}{self._cookie_separator}{self.access_token}"
