import datetime

from psycopg import errors as pgerrors

from odoo import api, fields, models
from odoo.orm.primitives import SUPERUSER_ID

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
                return 0, _EPOCH
            return row.failures, row.last_failure.replace(tzinfo=datetime.UTC)

    def record_failure(self, source: str, delay: datetime.timedelta) -> None:
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        with self.registry.cursor() as cr:
            rows = self._rows(cr)
            row = rows.search([("source", "=", source)], limit=1)
            if row:
                row.write({"failures": row.failures + 1, "last_failure": now})
            else:
                try:
                    with cr.savepoint():
                        rows.create(
                            {"source": source, "failures": 1, "last_failure": now}
                        )
                except pgerrors.UniqueViolation:
                    # two failures from one source in the same instant: the other
                    # transaction created the row, count ours on it
                    row = rows.search([("source", "=", source)], limit=1)
                    row.write({"failures": row.failures + 1, "last_failure": now})
            rows.search([("last_failure", "<", now - delay)]).unlink()

    def clear(self, source: str) -> None:
        with self.registry.cursor() as cr:
            self._rows(cr).search([("source", "=", source)]).unlink()
