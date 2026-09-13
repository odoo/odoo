import typing
from datetime import timedelta
from typing import Literal, Self

from psycopg.errors import UniqueViolation

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog
from odoo.service.transaction import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

if typing.TYPE_CHECKING:
    from .discuss.mail_guest import MailGuest
    from odoo.addons.bus.models.res_users import ResUsers

_debug = DebugLog(__name__)

IM_STATUS_PRIORITY = ("online", "away", "busy")
UPDATE_PRESENCE_DELAY = 60
DISCONNECTION_TIMER = UPDATE_PRESENCE_DELAY + 5
AWAY_TIMER = 1800
PRESENCE_OUTDATED_TIMER = 12 * 60 * 60


class MailPresence(models.Model):
    _name = "mail.presence"
    _inherit = "mixin.bus.listener"
    _description = "User/Guest Presence"
    _log_access = False

    user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Users",
        ondelete="cascade",
    )
    guest_id: MailGuest = fields.Many2one(
        comodel_name="mail.guest",
        ondelete="cascade",
    )
    last_poll = fields.Datetime(default=lambda self: fields.Datetime.now())
    last_presence = fields.Datetime(default=lambda self: fields.Datetime.now())
    status = fields.Selection(
        selection=[("online", "Online"), ("away", "Away"), ("offline", "Offline")],
        string="IM Status",
        default="offline",
    )

    _guest_unique = models.UniqueIndex("(guest_id) WHERE guest_id IS NOT NULL")
    _user_unique = models.UniqueIndex("(user_id) WHERE user_id IS NOT NULL")

    _partner_or_guest_exists = models.Constraint(
        "CHECK((user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL))",
        "A mail presence must have a user or a guest.",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        presences = super().create(vals_list)
        presences._send_presence()
        return presences

    def write(self, vals: ValuesType) -> Literal[True]:
        status_by_presence = {presence: presence.status for presence in self}
        result = super().write(vals)
        updated = self.filtered(lambda p: status_by_presence[p] != p.status)
        if _debug.lifecycle.enabled and updated:
            _debug.lifecycle(
                "status_changed", presences=updated.ids, status=vals.get("status")
            )
        updated._send_presence()
        return result

    def unlink(self) -> Literal[True]:
        guests_or_users = [presence.guest_id or presence.user_id for presence in self]
        res = super().unlink()
        for guest_or_user in guests_or_users:
            self._send_status_updated_notification(
                guest_or_user=guest_or_user, status="offline"
            )
        return res

    def _get_im_status(self, manual_im_status: str | Literal[False]) -> str:
        self.check_singleton()
        if self.status == "offline" or not self.status:
            return "offline"
        return manual_im_status or self.status

    def _fold_im_status(
        self, manual_im_status: str | Literal[False] | None = None
    ) -> str:
        statuses = {
            presence._get_im_status(
                presence.user_id.manual_im_status
                if manual_im_status is None
                else manual_im_status
            )
            for presence in self
        }
        return next(
            (status for status in IM_STATUS_PRIORITY if status in statuses), "offline"
        )

    @api.model
    def _try_update_presence(
        self, user_or_guest: ResUsers | MailGuest, inactivity_period: int = 0
    ) -> None:
        try:
            with tools.mute_logger("odoo.db"):
                self._update_presence(user_or_guest, inactivity_period)
                self.env.cr.commit()
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            _debug.logic(
                "presence_update_lost",
                target_model=user_or_guest._name,
                target=user_or_guest.id,
                reason="concurrency",
            )
            return self.env.cr.rollback()

    @api.model
    def _update_presence(
        self, user_or_guest: ResUsers | MailGuest, inactivity_period: int = 0
    ) -> None:
        values = {
            "last_poll": fields.Datetime.now(),
            "last_presence": fields.Datetime.now()
            - timedelta(milliseconds=inactivity_period),
            "status": "away" if inactivity_period > AWAY_TIMER * 1000 else "online",
        }
        user_or_guest_sudo = user_or_guest.sudo()
        if presence := user_or_guest_sudo.presence_ids:
            presence.write(values)
        else:
            values["guest_id" if user_or_guest._name == "mail.guest" else "user_id"] = (
                user_or_guest.id
            )
            try:
                with self.env.cr.savepoint():
                    self.env["mail.presence"].sudo().create(values)
            except UniqueViolation:
                _debug.logic(
                    "presence_raced",
                    target_model=user_or_guest._name,
                    target=user_or_guest.id,
                )
                user_or_guest_sudo.invalidate_recordset(["presence_ids"])
                user_or_guest_sudo.presence_ids.write(values)

    def _send_presence(
        self, im_status: str | None = None, bus_target: models.BaseModel | None = None
    ) -> None:
        for presence in self:
            self._send_status_updated_notification(
                guest_or_user=presence.guest_id or presence.user_id,
                status=im_status or presence.status,
                bus_target=bus_target,
            )

    @api.model
    def _send_status_updated_notification(
        self,
        *,
        guest_or_user: ResUsers | MailGuest,
        status: str,
        bus_target: models.BaseModel | None = None,
    ) -> None:
        identity_data = (
            {"guest_id": guest_or_user.id}
            if guest_or_user._name == "mail.guest"
            else {"partner_id": guest_or_user.partner_id.id}
        )
        (bus_target or guest_or_user)._bus_send(
            "bus.bus/im_status_updated",
            {
                "presence_status": status,
                "im_status": guest_or_user.im_status,
                **identity_data,
            },
            subchannel="presence" if not bus_target else None,
        )

    @api.autovacuum
    def _gc_bus_presence(self) -> None:
        outdated = self.search(
            [
                (
                    "last_poll",
                    "<",
                    fields.Datetime.now() - timedelta(seconds=PRESENCE_OUTDATED_TIMER),
                )
            ]
        )
        _debug.lifecycle("gc_presence", removed=len(outdated))
        outdated.unlink()
