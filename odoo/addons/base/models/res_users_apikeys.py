import binascii
import datetime
import logging
import os
from hashlib import sha256
from typing import Any, Self

from odoo import _, api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.password import CryptContext
from odoo.tools import SQL

from .res_users import check_identity

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

API_KEY_SIZE = 20
INDEX_SIZE = 8
KEY_CRYPT_CONTEXT = CryptContext(
    ["pbkdf2_sha512"],
    pbkdf2_sha512__rounds=6000,
)


class ResUsersApikeys(models.Model):
    _name = "res.users.apikeys"
    _description = "Users API Keys"
    _auto = False
    _allow_sudo_commands = False

    name = fields.Char(
        string="Description",
        readonly=True,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    scope = fields.Char(readonly=True)
    create_date = fields.Datetime(
        string="Creation Date",
        readonly=True,
    )
    expiration_date = fields.Datetime(readonly=True)

    def init(self) -> None:
        table = SQL.identifier(self._table)
        self.env.cr.execute(
            SQL(
                f"""
                CREATE TABLE IF NOT EXISTS %s (
                    id serial primary key,
                    name varchar not null,
                    user_id integer not null REFERENCES res_users(id) ON DELETE CASCADE,
                    scope varchar,
                    expiration_date timestamp without time zone,
                    index varchar({INDEX_SIZE}) not null CHECK (char_length(index) = {INDEX_SIZE}),
                    key varchar not null,
                    create_date timestamp without time zone DEFAULT (now() at time zone 'UTC')
                )
                """,
                table,
            )
        )

        index_name = self._table + "_user_id_index_idx"
        if len(index_name) > 63:
            index_name = (
                self._table[:50]
                + "_idx_"
                + sha256(self._table.encode()).hexdigest()[:8]
            )
        self.env.cr.execute(
            SQL(
                "CREATE INDEX IF NOT EXISTS %s ON %s (user_id, index)",
                SQL.identifier(index_name),
                table,
            )
        )

    @check_identity
    def remove(self) -> dict[str, str]:
        return self._remove()

    def _remove(self) -> dict[str, str]:
        if not self:
            _debug.logic("apikeys_remove_noop", uid=self.env.uid)
            return {"type": "ir.actions.act_window_close"}
        if self.env.is_system() or self.mapped("user_id") == self.env.user:
            ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"
            _logger.info(
                "API key(s) removed: scope: <%s> for '%s' (#%s) from %s",
                self.mapped("scope"),
                self.env.user.login,
                self.env.uid,
                ip,
            )
            _debug.lifecycle("apikeys_removed", count=len(self), by=self.env.uid)
            self.sudo().unlink()
            return {"type": "ir.actions.act_window_close"}
        _debug.logic(
            "apikeys_remove_refused",
            uid=self.env.uid,
            owners=self.mapped("user_id").ids,
        )
        raise AccessError(
            _(
                "You can not remove API keys unless they're yours or you are a system user"
            )
        )

    def unlink(self) -> bool:
        _debug.lifecycle("apikeys_unlinked", count=len(self))
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    def _match_key(
        self, scope: str, key: str, *, include_expired: bool
    ) -> tuple[int, datetime.datetime | None] | None:
        self.env.cr.execute(
            SQL(
                """
                SELECT user_id, key, expiration_date
                FROM %s INNER JOIN res_users u ON (u.id = user_id)
                WHERE u.active AND index = %s AND (scope IS NULL OR scope = %s) %s
                """,
                SQL.identifier(self._table),
                key[:INDEX_SIZE],
                scope,
                SQL()
                if include_expired
                else SQL(
                    "AND (expiration_date IS NULL"
                    " OR expiration_date >= now() at time zone 'utc')"
                ),
            )
        )
        candidates = self.env.cr.fetchall()
        _debug.perf.count(
            "apikey_candidates",
            scope=scope,
            candidates=len(candidates),
            include_expired=include_expired,
        )
        for user_id, current_key, expiration_date in candidates:
            if KEY_CRYPT_CONTEXT.is_password_valid(key, current_key):
                _debug.logic(
                    "apikey_matched", scope=scope, uid=user_id, expires=expiration_date
                )
                return user_id, expiration_date
        _debug.logic("apikey_rejected", scope=scope, candidates=len(candidates))
        return None

    def _check_credentials(self, *, scope: str, key: str) -> int | None:
        if not scope or not key:
            _debug.logic("apikey_check_refused", reason="missing_scope_or_key")
            msg = "scope and key required"
            raise ValueError(msg)
        match = self._match_key(scope, key, include_expired=False)
        return match[0] if match else None

    def _get_key_expiration(self, *, scope: str, key: str) -> datetime.datetime | None:
        if not scope or not key:
            return None
        match = self._match_key(scope, key, include_expired=True)
        return match[1] if match else None

    def _get_max_duration(self) -> float:
        return (
            max(
                (group.api_key_duration for group in self.env.user.all_group_ids),
                default=0.0,
            )
            or 1.0
        )

    def _check_expiration_date(self, date: datetime.datetime | None) -> None:
        if self.env.is_system():
            _debug.logic(
                "apikey_expiration_unchecked", uid=self.env.uid, reason="system"
            )
            return
        if not date:
            _debug.logic("apikey_expiration_rejected", uid=self.env.uid, reason="unset")
            raise ValidationError(_("The API key must have an expiration date"))
        max_duration = self._get_max_duration()
        if date > fields.Datetime.now() + datetime.timedelta(days=max_duration):
            _debug.logic(
                "apikey_expiration_rejected",
                uid=self.env.uid,
                reason="too_far",
                max_days=max_duration,
            )
            raise ValidationError(
                _("You cannot exceed %(duration)s days.", duration=max_duration)
            )

    def _check_generate_access(self) -> None:
        if not self.env.user._is_internal():
            _debug.logic("apikey_generate_refused", uid=self.env.uid)
            raise AccessError(_("Only internal users can create API keys"))

    def _generate(
        self,
        scope: str | None,
        name: str,
        expiration_date: datetime.datetime | None,
    ) -> str:
        self._check_generate_access()
        self._check_expiration_date(expiration_date)
        k = binascii.hexlify(os.urandom(API_KEY_SIZE)).decode()
        self.env.cr.execute(
            SQL(
                """
                INSERT INTO %s (name, user_id, scope, expiration_date, key, index)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                SQL.identifier(self._table),
                name,
                self.env.user.id,
                scope,
                expiration_date or None,
                KEY_CRYPT_CONTEXT.hash(k),
                k[:INDEX_SIZE],
            )
        )

        self.env.user.invalidate_recordset(["api_key_ids"])
        _debug.pipeline("apikey_inserted", uid=self.env.uid, scope=scope)

        ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"
        _logger.info(
            "%s generated: scope: <%s> for '%s' (#%s) from %s",
            self._description,
            scope,
            self.env.user.login,
            self.env.uid,
            ip,
        )
        _debug.lifecycle(
            "apikey_generated", uid=self.env.uid, scope=scope, expires=expiration_date
        )

        return k

    @api.autovacuum
    def _gc_user_apikeys(self) -> None:
        self.env.cr.execute(
            SQL(
                """
            DELETE FROM %s
            WHERE
                expiration_date IS NOT NULL AND
                expiration_date < now() at time zone 'utc'
        """,
                SQL.identifier(self._table),
            )
        )
        count = self.env.cr.rowcount
        if count:
            self.env.registry.clear_cache()
        _logger.info("GC %r delete %d entries", self._name, count)
        _debug.lifecycle("gc_apikeys", count=count)


class ResUsersApikeysDescription(models.TransientModel):
    _name = "res.users.apikeys.description"
    _description = "API Key Description"

    def _selection_duration(self) -> list[tuple[str, str]]:
        durations = [
            ("1", "1 Day"),
            ("7", "1 Week"),
            ("30", "1 Month"),
            ("90", "3 Months"),
            ("180", "6 Months"),
            ("365", "1 Year"),
        ]
        persistent_duration = (
            "0",
            "Persistent Key",
        )
        custom_duration = (
            "-1",
            "Custom Date",
        )
        if self.env.is_system():
            return durations + [persistent_duration, custom_duration]
        max_duration = self.env["res.users.apikeys"]._get_max_duration()
        offered = list(
            filter(lambda duration: int(duration[0]) <= max_duration, durations)
        ) + [custom_duration]
        _debug.logic(
            "apikey_durations_offered",
            uid=self.env.uid,
            max_days=max_duration,
            offered=len(offered),
        )
        return offered

    name = fields.Char(
        string="Description",
        required=True,
    )
    duration = fields.Selection(
        selection="_selection_duration",
        default=lambda self: self._selection_duration()[0][0],
        required=True,
    )
    expiration_date = fields.Datetime(
        compute="_compute_expiration_date",
        store=True,
        readonly=False,
    )

    @api.depends("duration")
    def _compute_expiration_date(self) -> None:
        for record in self:
            duration = int(record.duration)
            if duration >= 0:
                record.expiration_date = (
                    fields.Datetime.now() + datetime.timedelta(days=duration)
                    if duration
                    else None
                )

    @api.onchange("expiration_date")
    def _onchange_expiration_date(self) -> dict[str, Any] | None:
        try:
            self.env["res.users.apikeys"]._check_expiration_date(self.expiration_date)
        except UserError as error:
            _debug.logic("apikey_expiration_onchange_warned", uid=self.env.uid)
            warning = {
                "type": "notification",
                "title": _("The API key duration is not correct."),
                "message": error.args[0],
            }
            return {"warning": warning}

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        records = super().create(vals_list)
        _debug.lifecycle("apikey_description_created", count=len(records))
        apikeys = self.env["res.users.apikeys"]
        for record in records:
            apikeys._check_expiration_date(record.expiration_date)
        return records

    @check_identity
    def action_generate_key(self) -> dict[str, Any]:
        self.check_access_generate_key()

        description = self.sudo()
        k = self.env["res.users.apikeys"]._generate(
            None, description.name, self.expiration_date
        )
        _debug.lifecycle("apikey_wizard_done", uid=self.env.uid, wizard=self.id)
        description.unlink()

        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.apikeys.show",
            "name": _("API Key Ready"),
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_key": k,
            },
        }

    def check_access_generate_key(self) -> None:
        self.env["res.users.apikeys"]._check_generate_access()


class ResUsersApikeysShow(models.AbstractModel):
    _name = "res.users.apikeys.show"
    _description = "Show API Key"

    id = fields.Id()
    key = fields.Char(readonly=True)
