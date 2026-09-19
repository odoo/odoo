import logging
import re
from collections import Counter
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PURPOSE_RE = re.compile(r"^[a-z][a-z0-9_]*(?::[a-z0-9_.]+)*$")

PURPOSE_MAX_LENGTH = 64

_PENDING_KEY = "credential.use.pending"


def check_purpose(purpose: str) -> str:
    if (
        not isinstance(purpose, str)
        or len(purpose) > PURPOSE_MAX_LENGTH
        or not PURPOSE_RE.match(purpose)
    ):
        raise ValueError(
            f"a secret use needs a purpose such as 'integration:bearer' or "
            f"'env:claude_sdk' (lowercase, at most {PURPOSE_MAX_LENGTH} characters), "
            f"got {purpose!r}"
        )
    return purpose


def _flush(registry, pending: Counter) -> None:
    if not pending:
        return
    rows = list(pending.items())
    pending.clear()
    try:
        with registry.cursor() as cr:
            for (credential_id, purpose, day), count in rows:
                cr.execute(
                    """
                    INSERT INTO credential_use
                           (credential_id, purpose, day, use_count, last_used_at)
                    SELECT id, %s, %s, %s, now() AT TIME ZONE 'UTC'
                      FROM credential_credential
                     WHERE id = %s
                        ON CONFLICT (credential_id, purpose, day) DO UPDATE
                       SET use_count = credential_use.use_count + EXCLUDED.use_count,
                           last_used_at = EXCLUDED.last_used_at
                    """,
                    (purpose, day, count, credential_id),
                )
    except Exception:
        _logger.exception(
            "Could not record %s secret use(s); the uses themselves went ahead",
            sum(count for _key, count in rows),
        )


class CredentialUse(models.Model):
    _name = "credential.use"
    _description = "Secret Uses per Day"
    _order = "day desc, credential_id, purpose"
    _log_access = False

    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    purpose = fields.Char(
        readonly=True,
        required=True,
        help="What the server code used the secret for, as it declared it.",
    )
    day = fields.Date(
        index=True,
        readonly=True,
        required=True,
        help="UTC day the uses fall on.",
    )
    use_count = fields.Integer(
        string="Uses",
        readonly=True,
    )
    last_used_at = fields.Datetime(readonly=True)
    company_id = fields.Many2one(
        related="credential_id.company_id",
    )

    _credential_purpose_day_uniq = models.Constraint(
        "UNIQUE(credential_id, purpose, day)",
        "One row counts a credential's uses for one purpose on one day.",
    )

    @api.depends("credential_id", "purpose", "day")
    def _compute_display_name(self):
        for use in self:
            use.display_name = (
                f"{use.credential_id.display_name} · {use.purpose} · {use.day}"
            )

    @api.model
    def _queue(self, credential_id: int, purpose: str) -> None:
        cr = self.env.cr
        pending = cr.postcommit.data.get(_PENDING_KEY)
        if pending is None:
            pending = Counter()
            cr.postcommit.data[_PENDING_KEY] = pending
            registry = self.env.registry
            cr.postcommit.add(lambda: _flush(registry, pending))
            cr.postrollback.add(lambda: _flush(registry, pending))
        pending[(credential_id, purpose, fields.Date.today())] += 1

    @api.model
    def cron_gc_uses(self, retention_days: int = 400) -> int:
        threshold = fields.Date.today() - timedelta(days=retention_days)
        old = self.search([("day", "<", threshold)])
        count = len(old)
        old.unlink()
        return count
