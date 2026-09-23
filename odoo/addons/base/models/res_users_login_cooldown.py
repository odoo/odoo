import datetime

from odoo import SUPERUSER_ID, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)

_EPOCH = datetime.datetime.min.replace(tzinfo=datetime.UTC)


class ResUsersLoginCooldown(models.Model):
    _name = "res.users.login.cooldown"
    _description = "Login Failure Cooldown"
    _log_access = False

    source = fields.Char(
        index="btree",
        required=True,
    )
    failures = fields.Integer(
        default=0,
        required=True,
    )
    last_failure = fields.Datetime(
        index="btree",
        required=True,
    )

    _source_uniq = models.Constraint(
        "unique (source)",
        "There can be only one cooldown row per source.",
    )


class LoginCooldown:
    """The login-failure ledger, kept in its own transaction: a failed login
    rolls its transaction back, and the failure has to outlive it."""

    __slots__ = ("registry",)

    def __init__(self, registry) -> None:
        self.registry = registry

    def _rows(self, cr):
        env = api.Environment(cr, SUPERUSER_ID, {})
        return env["res.users.login.cooldown"]

    def state(self, source: str) -> tuple[int, datetime.datetime]:
        with self.registry.cursor() as cr:
            row = self._rows(cr).search([("source", "=", source)], limit=1)
            if not row:
                _debug.logic("cooldown_state", source=source, failures=0)
                return 0, _EPOCH
            _debug.logic("cooldown_state", source=source, failures=row.failures)
            return row.failures, row.last_failure.replace(tzinfo=datetime.UTC)

    def record_failure(self, source: str, delay: datetime.timedelta) -> None:
        now = fields.Datetime.now()
        with self.registry.cursor() as cr:
            # a concurrent failure from the same source must be counted, not
            # lost to a snapshot taken before its row was committed
            cr.use_read_committed()
            cr.execute(
                SQL(
                    """
                    INSERT INTO res_users_login_cooldown (source, failures, last_failure)
                    VALUES (%s, 1, %s)
                    ON CONFLICT (source) DO UPDATE
                    SET failures = res_users_login_cooldown.failures + 1,
                        last_failure = EXCLUDED.last_failure
                    RETURNING failures
                    """,
                    source,
                    now,
                )
            )
            _debug.lifecycle(
                "cooldown_failure_counted", source=source, failures=cr.fetchone()[0]
            )
            expired = self._rows(cr).search([("last_failure", "<", now - delay)])
            _debug.lifecycle("cooldown_rows_expired", count=len(expired))
            expired.unlink()

    def clear(self, source: str) -> None:
        with self.registry.cursor() as cr:
            rows = self._rows(cr).search([("source", "=", source)])
            _debug.lifecycle("cooldown_cleared", source=source, rows=len(rows))
            rows.unlink()
