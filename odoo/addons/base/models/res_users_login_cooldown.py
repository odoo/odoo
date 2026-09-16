import datetime

from psycopg import errors as pgerrors

from odoo import SUPERUSER_ID, api, fields, models
from odoo.libs.debug_log import DebugLog

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
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        with self.registry.cursor() as cr:
            rows = self._rows(cr)
            row = rows.search([("source", "=", source)], limit=1)
            if row:
                _debug.lifecycle(
                    "cooldown_failure_counted", source=source, failures=row.failures + 1
                )
                row.write({"failures": row.failures + 1, "last_failure": now})
            else:
                try:
                    with cr.savepoint():
                        rows.create(
                            {"source": source, "failures": 1, "last_failure": now}
                        )
                    _debug.lifecycle("cooldown_row_created", source=source)
                except pgerrors.UniqueViolation:
                    # two failures from one source in the same instant: the other
                    # transaction created the row, count ours on it
                    _debug.logic("cooldown_row_raced", source=source)
                    row = rows.search([("source", "=", source)], limit=1)
                    row.write({"failures": row.failures + 1, "last_failure": now})
            expired = rows.search([("last_failure", "<", now - delay)])
            _debug.lifecycle("cooldown_rows_expired", count=len(expired))
            expired.unlink()

    def clear(self, source: str) -> None:
        with self.registry.cursor() as cr:
            rows = self._rows(cr).search([("source", "=", source)])
            _debug.lifecycle("cooldown_cleared", source=source, rows=len(rows))
            rows.unlink()
