import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InboundAccessLog(models.Model):
    _name = "inbound.access.log"
    _description = "Inbound Access Log"
    _order = "timestamp desc, id desc"
    _rec_name = "display_name"

    _CLEANUP_CONTEXT_KEY = "_inbound_log_cleanup_bypass"

    _COLLAPSE_FIELDS = frozenset({"attempt_count", "last_seen_at"})

    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        ondelete="cascade",
    )
    timestamp = fields.Datetime(
        string="First Seen",
        default=fields.Datetime.now,
        index=True,
        required=True,
    )
    last_seen_at = fields.Datetime(
        help="Same as First Seen unless this row collapses repeated refusals "
        "AND those refusals are counted. Audit-mode admissions are collapsed "
        "but not counted, so on those rows it stays equal to First Seen."
    )

    gate_model = fields.Char(
        index=True,
        required=True,
    )
    gate_id = fields.Integer(
        index=True,
        required=True,
    )
    gate_name = fields.Char()

    allowed = fields.Boolean(index=True)
    outcome = fields.Selection(
        selection=[
            ("allowed", "Allowed"),
            ("audit_accepted", "Accepted unauthenticated (audit mode)"),
            ("misconfigured", "Refused: gate cannot authenticate anything"),
            ("caller_limited", "Refused: caller rate limit"),
            ("address_refused", "Refused: address not allowed"),
            ("payload_too_large", "Refused: payload too large"),
            ("rate_limited", "Refused: endpoint rate limit"),
            ("unauthenticated", "Refused: authentication failed"),
            ("unknown_receiver", "Refused: no such receiver"),
        ],
        index=True,
        required=True,
        help="The verdict, categorised so it can be grouped and alerted on "
        "without parsing the reason text. `misconfigured` and "
        "`unauthenticated` are both 401s and were once the same value: the "
        "first is the gate refusing everything because its own configuration "
        "is incomplete, the second is a caller presenting bad credentials. "
        "They are separated because only the first is a standing condition.",
    )
    status_code = fields.Integer()
    reason = fields.Char(
        help="The gate's own words. Empty when the request was allowed."
    )
    attempt_count = fields.Integer(
        default=1,
        help="Requests this row stands for. Above 1 only where repeated "
        "refusals from one caller were collapsed into a single row. It stays "
        "at 1 on an audit-mode row, which stands for a whole window of "
        "admissions but does not count them: counting is an UPDATE of a row "
        "every concurrent request shares, and on an ingest path that is a "
        "serialisation failure per burst.",
    )

    source_ip = fields.Char(
        index=True,
        help="The caller. On a row that stands for repeated audit-mode "
        "admissions this is the first one seen in the window, not the only "
        "one: what that row records is the gate having no credential.",
    )
    user_agent = fields.Char()
    auth_type = fields.Char(
        help="The scheme the gate was configured to require, snapshotted."
    )
    mode = fields.Char(
        help="enforce or audit. `off` is not recorded: the gate did not run."
    )

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("gate_name", "outcome", "source_ip", "attempt_count")
    def _compute_display_name(self):
        for log in self:
            times = f" ×{log.attempt_count}" if log.attempt_count > 1 else ""
            source = log.source_ip or "unknown source"
            label = dict(self._fields["outcome"].selection).get(
                log.outcome, log.outcome or ""
            )
            log.display_name = (
                f"{log.gate_name or log.gate_model}: {label} from {source}{times}"
            )

    def _is_cleanup_authorized(self) -> bool:
        return bool(self.env.context.get(self._CLEANUP_CONTEXT_KEY)) and self.env.su

    def write(self, vals):
        editable = set(vals) - self._COLLAPSE_FIELDS - {"display_name"}
        if editable and not self._is_cleanup_authorized():
            raise UserError(
                self.env._(
                    "Inbound access log entries cannot be modified: %(fields)s",
                    fields=", ".join(sorted(editable)),
                )
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _refuse_delete_outside_cleanup(self):
        if self and not self._is_cleanup_authorized():
            raise UserError(
                self.env._(
                    "Inbound access log entries cannot be deleted. They are "
                    "removed by the retention cron once they age out."
                )
            )

    REFUSED_CALLER_WINDOW_SECONDS = 3600

    @api.model
    def _record_unknown_caller(
        self,
        receiver_model: str,
        label: str,
        remote_addr: str | None,
        user_agent: str | None = None,
        status_code: int = 404,
    ) -> None:
        self._record_refused_caller(
            receiver_model,
            label,
            remote_addr,
            outcome="unknown_receiver",
            reason=f"no active {receiver_model} for {label}",
            user_agent=user_agent,
            status_code=status_code,
        )

    @api.model
    def _record_refused_caller(
        self,
        gate_model: str,
        label: str,
        remote_addr: str | None,
        outcome: str,
        reason: str,
        user_agent: str | None = None,
        status_code: int = 401,
    ) -> None:
        logs = self.sudo()
        now = fields.Datetime.now()
        standing = logs.search(
            [
                ("gate_model", "=", gate_model),
                ("gate_id", "=", 0),
                ("outcome", "=", outcome),
                ("source_ip", "=", remote_addr or False),
                (
                    "timestamp",
                    ">=",
                    fields.Datetime.subtract(
                        now, seconds=self.REFUSED_CALLER_WINDOW_SECONDS
                    ),
                ),
            ],
            order="timestamp desc",
            limit=1,
        )
        if standing:
            standing.write(
                {"attempt_count": standing.attempt_count + 1, "last_seen_at": now}
            )
            return
        logs.create(
            {
                "gate_model": gate_model,
                "gate_id": 0,
                "gate_name": (label or "")[:128] or False,
                "timestamp": now,
                "last_seen_at": now,
                "allowed": False,
                "outcome": outcome,
                "status_code": status_code,
                "reason": (reason or "")[:256] or False,
                "source_ip": remote_addr or False,
                "user_agent": (user_agent or "")[:256] or False,
                "mode": "enforce",
            }
        )

    @api.model
    def cron_gc_inbound_access_logs(self, retention_days: int = 365):
        cutoff = fields.Datetime.now() - timedelta(days=retention_days)
        sudo_self = self.sudo()
        stale = sudo_self.search([("timestamp", "<", cutoff)])
        count = len(stale)
        if stale:
            stale.with_context(**{self._CLEANUP_CONTEXT_KEY: True}).unlink()
            _logger.info(
                "Removed %s inbound access log entries past %sd", count, retention_days
            )
        return count
