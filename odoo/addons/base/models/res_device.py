import logging
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from typing import Any

from odoo import api, fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.exceptions import AccessError
from odoo.fields import Field
from odoo.http import (
    STORED_SESSION_BYTES,
    GeoIP,
    get_session_max_inactivity,
    request,
    root,
)
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, unique
from odoo.tools.translate import _

from .res_users import check_identity

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_MOBILE_PLATFORMS = frozenset(
    {
        "android",
        "iphone",
        "ipad",
        "ipod",
        "blackberry",
        "windows phone",
        "webos",
    }
)

_DEVICE_IDENTITY_COLUMNS = (
    ("user_id", True),
    ("session_identifier", False),
    ("platform", True),
    ("browser", True),
)


class ResDeviceLog(models.Model):
    _name = "res.device.log"
    _description = "Device Log"
    _rec_names_search = ["platform", "browser"]

    session_identifier = fields.Char(
        index="btree",
        required=True,
    )
    platform = fields.Char()
    browser = fields.Char()
    ip_address = fields.Char(string="IP Address")
    country = fields.Char()
    city = fields.Char()
    device_type = fields.Selection(
        selection=[("computer", "Computer"), ("mobile", "Mobile")]
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index="btree",
        ondelete="cascade",
    )
    first_activity = fields.Datetime()
    last_activity = fields.Datetime(index="btree")
    revoked = fields.Boolean(
        help="If True, the session file corresponding to this device"
        " no longer exists on the filesystem."
    )
    is_current = fields.Boolean(
        string="Current Device",
        compute="_compute_is_current",
        order_by_sql="_is_current_order_sql",
    )
    linked_ip_addresses = fields.Text(
        string="Linked IP address",
        compute="_compute_linked_ip_addresses",
    )

    _composite_idx = models.Index(
        "(user_id, session_identifier, platform, browser, last_activity, id) WHERE revoked IS NOT TRUE"
    )
    _revoked_idx = models.Index("(revoked) WHERE revoked IS NOT TRUE")

    @api.depends("platform", "browser")
    def _compute_display_name(self) -> None:
        for device in self:
            platform = device.platform or _("Unknown")
            browser = device.browser or _("Unknown")
            device.display_name = f"{platform.capitalize()} {browser.capitalize()}"

    @api.depends("session_identifier")
    def _compute_is_current(self) -> None:
        for device in self:
            device.is_current = request and request.session.sid.startswith(
                device.session_identifier
            )

    @api.depends("session_identifier", "platform", "browser")
    def _compute_linked_ip_addresses(self) -> None:
        device_group_map = {}
        for *device_info, ip_array in self.env["res.device.log"]._read_group(
            domain=[("session_identifier", "in", self.mapped("session_identifier"))],
            groupby=["session_identifier", "platform", "browser"],
            aggregates=["ip_address:array_agg"],
        ):
            device_group_map[tuple(device_info)] = ip_array
        _debug.perf.count(
            "linked_ip_addresses_computed",
            devices=len(self),
            groups=len(device_group_map),
        )
        for device in self:
            device.linked_ip_addresses = "\n".join(
                OrderedSet(
                    ip
                    for ip in device_group_map.get(
                        (
                            device.session_identifier,
                            device.platform,
                            device.browser,
                        ),
                        [],
                    )
                    if ip
                )
            )

    def _is_current_order_sql(
        self, field: Field, alias: str, direction: Any, nulls: Any, query: Any
    ) -> SQL:
        if not (request and request.session.sid):
            # no session to compare against: the term sorts nothing
            return SQL.EMPTY
        _debug.logic("order_by_is_current", direction=str(direction))
        return SQL(
            "%s = %s %s",
            SQL.identifier(alias, "session_identifier"),
            request.session.sid[:STORED_SESSION_BYTES],
            direction,
        )

    def _is_mobile(self, platform: str | None) -> bool:
        if not platform:
            return False
        return platform.lower() in _MOBILE_PLATFORMS

    @api.model
    def _update_device(self, request: Any) -> None:
        trace = request.session.update_trace(request)
        if not trace:
            _debug.logic("device_log_skipped", reason="trace_unchanged")
            return

        geoip = GeoIP(trace["ip_address"], app=request.app)
        user_id = request.session.uid
        session_identifier = request.session.sid[:STORED_SESSION_BYTES]

        _debug.logic(
            "device_log_cursor",
            uid=user_id,
            own_cursor=bool(self.env.cr.readonly),
            mobile=self._is_mobile(trace["platform"]),
        )
        if self.env.cr.readonly:
            cursor = self.env.registry.cursor(readonly=False)
        else:
            cursor = nullcontext(self.env.cr)
        # Contain this optional SQL write without adding savepoints to requests
        # whose trace did not change, or flushing unrelated pending ORM work.
        with cursor as cr, cr.savepoint(flush=False):
            cr.execute(
                SQL(
                    """
                INSERT INTO res_device_log (session_identifier, platform, browser, ip_address, country, city, device_type, user_id, first_activity, last_activity, revoked)
                VALUES (%(session_identifier)s, %(platform)s, %(browser)s, %(ip_address)s, %(country)s, %(city)s, %(device_type)s, %(user_id)s, %(first_activity)s, %(last_activity)s, %(revoked)s)
            """,
                    session_identifier=session_identifier,
                    platform=trace["platform"],
                    browser=trace["browser"],
                    ip_address=trace["ip_address"],
                    country=geoip.get("country_name"),
                    city=geoip.get("city"),
                    device_type=(
                        "mobile" if self._is_mobile(trace["platform"]) else "computer"
                    ),
                    user_id=user_id,
                    first_activity=datetime.fromtimestamp(
                        trace["first_activity"], tz=UTC
                    ).replace(tzinfo=None),
                    last_activity=datetime.fromtimestamp(
                        trace["last_activity"], tz=UTC
                    ).replace(tzinfo=None),
                    revoked=False,
                )
            )
        _logger.info("User %d inserts device log (%s)", user_id, session_identifier)
        _debug.lifecycle(
            "device_log_inserted",
            uid=user_id,
            platform=trace["platform"],
            browser=trace["browser"],
            readonly_cursor=self.env.cr.readonly,
        )

    @api.autovacuum
    def _gc_device_log(self) -> None:
        partition_columns = SQL(", ").join(
            SQL.identifier(column) for column, _nullable in _DEVICE_IDENTITY_COLUMNS
        )
        self.env.cr.execute(
            SQL(
                """
            DELETE FROM res_device_log
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id,
                           row_number() OVER (
                               PARTITION BY %(partition_columns)s, ip_address
                               ORDER BY last_activity DESC, id DESC
                           ) AS rn
                    FROM res_device_log
                ) ranked
                WHERE ranked.rn > 1
            )
        """,
                partition_columns=partition_columns,
            )
        )
        _logger.info("GC device logs delete %d entries", self.env.cr.rowcount)
        _debug.lifecycle("gc_device_logs", count=self.env.cr.rowcount)

    @api.autovacuum
    def _update_revoked(self) -> None:
        batch_size = 100_000
        offset = 0

        while True:
            candidate_device_log_ids = self.env["res.device.log"].search_fetch(
                [
                    ("revoked", "=", False),
                    (
                        "last_activity",
                        "<",
                        fields.Datetime.now()
                        - timedelta(seconds=get_session_max_inactivity(self.env)),
                    ),
                ],
                ["session_identifier"],
                order="id",
                limit=batch_size,
                offset=offset,
            )
            if not candidate_device_log_ids:
                _debug.lifecycle("revoke_sweep_done", offset=offset)
                break
            offset += batch_size
            revoked_session_identifiers = (
                root.session_store.get_missing_session_identifiers(
                    set(candidate_device_log_ids.mapped("session_identifier"))
                )
            )
            _debug.pipeline(
                "revoke_sweep",
                candidates=len(candidate_device_log_ids),
                missing_sessions=len(revoked_session_identifiers),
            )
            if revoked_session_identifiers:
                to_revoke = candidate_device_log_ids.filtered(
                    lambda candidate, revoked=revoked_session_identifiers: (
                        candidate.session_identifier in revoked
                    )
                )
                to_revoke.write({"revoked": True})
                self.env.cr.commit()
                offset -= len(to_revoke)
                _debug.lifecycle("device_logs_revoked", count=len(to_revoke), by="gc")


class ResDevice(models.Model):
    _name = "res.device"
    _inherit = ["res.device.log"]
    _description = "Devices"
    _auto = False
    _order = "last_activity desc"

    @check_identity
    def revoke(self) -> None:
        return self._revoke()

    def _revoke(self) -> None:
        if not self:
            _debug.logic("revoke_skipped", uid=self.env.uid, reason="empty_recordset")
            return
        if not self.env.is_system() and self.mapped("user_id") != self.env.user:
            _debug.logic("revoke_refused", uid=self.env.uid, devices=self.ids)
            raise AccessError(_("You can only revoke your own devices."))
        ResDeviceLog = self.env["res.device.log"]
        session_identifiers = list(unique(device.session_identifier for device in self))
        root.session_store.remove_sessions_for_identifiers(session_identifiers)
        revoked_devices = ResDeviceLog.sudo().search(
            [("session_identifier", "in", session_identifiers)]
        )
        revoked_devices.write({"revoked": True})
        _logger.info(
            "User %d revokes devices (%s)",
            self.env.uid,
            ", ".join(session_identifiers),
        )

        must_logout = bool(self.filtered("is_current"))
        _debug.lifecycle(
            "devices_revoked",
            uid=self.env.uid,
            sessions=len(session_identifiers),
            logs=len(revoked_devices),
            logout=must_logout,
        )
        if must_logout:
            request.session.logout()

    @api.model
    def _select(self) -> str:
        return "SELECT D.*"

    @api.model
    def _from(self) -> str:
        return "FROM res_device_log D"

    @api.model
    def _where(self) -> str:
        identity_join = "\n                        AND ".join(
            f"D2.{column} IS NOT DISTINCT FROM D.{column}"
            if nullable
            else f"D2.{column} = D.{column}"
            for column, nullable in _DEVICE_IDENTITY_COLUMNS
        )
        return f"""
            WHERE
                NOT EXISTS (
                    SELECT 1
                    FROM res_device_log D2
                    WHERE
                        {identity_join}
                        AND (
                            D2.last_activity > D.last_activity
                            OR (D2.last_activity = D.last_activity AND D2.id > D.id)
                        )
                        AND D2.revoked IS NOT TRUE
                )
                AND D.revoked IS NOT TRUE
        """

    @property
    def _query(self):
        return f"{self._select()} {self._from()} {self._where()}"

    def init(self) -> None:
        drop_view_if_exists(self.env.cr, self._table)
        _debug.lifecycle("view_recreated", table=self._table)
        self.env.cr.execute(
            SQL(
                """
            CREATE or REPLACE VIEW %s as (%s)
        """,
                SQL.identifier(self._table),
                SQL(self._query),
            )
        )
