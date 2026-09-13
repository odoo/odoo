import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CredentialAccessLog(models.Model):
    _name = "credential.access.log"
    _description = "Credential Access Log"
    _order = "timestamp desc"
    _rec_name = "credential_id"

    _CLEANUP_CONTEXT_KEY = "_credential_log_cleanup_bypass"

    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        required=False,
        ondelete="cascade",
        help="Company context for the access (empty for system-wide credentials)",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=False,
        ondelete="set null",
        help="User who accessed the credential. Nullable with ondelete=set "
        "null so deleting a user does NOT erase the audit trail of what they "
        "accessed; the login is denormalized into user_login for readability.",
    )
    user_login = fields.Char(
        help="Login of the accessing user, captured at access time. Survives "
        "deletion of the res.users record so the audit row stays readable."
    )
    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        index=True,
        required=False,
        ondelete="set null",
        help="Credential that was accessed. Nullable with ondelete=set null: "
        "an audit trail MUST outlive the credential it describes, so deleting "
        "a credential nulls this FK instead of cascade-wiping its history. The "
        "name is denormalized into credential_name so the row stays readable.",
    )
    credential_name = fields.Char(
        index=True,
        help="Name of the accessed credential, captured at access time. "
        "Survives deletion of the credential so the audit row stays readable.",
    )
    operation = fields.Selection(
        selection=[
            ("read", "Read"),
            ("write", "Write"),
            ("validate", "Validate"),
            ("use", "Use"),
            ("delete", "Delete"),
            ("read_rate_limited", "Read (Rate Limited)"),
        ],
        index=True,
        required=True,
        help="Type of operation performed",
    )
    DENIED_OPERATIONS = {
        "read_rate_limited": "Decryption rate limit exceeded for this user",
    }

    timestamp = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        required=True,
        help="When the access occurred",
    )
    source_ip = fields.Char(
        string="Source IP",
        index=True,
        help="IP address of the request origin (if available)",
    )
    display_name = fields.Char(
        compute="_compute_display_name",
        store=False,
    )

    _timestamp_credential_idx = models.Index("(timestamp, credential_id)")

    def write(self, vals):
        protected_fields = set(vals.keys()) - {"display_name"}

        if protected_fields and not self._is_cleanup_authorized():
            raise UserError(
                self.env._(
                    "Audit log records cannot be modified!\n\n"
                    "Credential access logs are immutable to ensure audit trail "
                    "integrity. This is a security feature.\n\n"
                    "Attempted to modify: %(fields)s",
                )
                % {"fields": ", ".join(sorted(protected_fields))},
            )

        return super().write(vals)

    def unlink(self):
        if self and not self._is_cleanup_authorized():
            raise UserError(  # pylint: disable=raise-unlink-override,no-raise-unlink,E8503
                self.env._(
                    "Audit log records cannot be deleted!\n\n"
                    "Credential access logs must be preserved for security auditing "
                    "and compliance. This is a security feature.\n\n"
                    "If you need to remove old logs, use the automated cleanup "
                    "scheduled action which respects retention policies.",
                ),
            )

        return super().unlink()

    @api.depends("credential_id", "credential_name", "operation", "timestamp")
    def _compute_display_name(self) -> None:
        for record in self:
            if record.timestamp:
                timestamp_str = record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = "Unknown"
            cred_label = (
                record.credential_id.name or record.credential_name or "(deleted)"
            )
            record.display_name = (
                f"{cred_label} - {record.operation} at {timestamp_str}"
            )

    def cron_cleanup_old_logs(self, retention_days: int = 365):
        cutoff_date = fields.Datetime.now() - timedelta(days=retention_days)

        sudo_self = self.sudo()
        old_logs = sudo_self.search([("timestamp", "<", cutoff_date)])
        count = len(old_logs)

        if old_logs:
            old_logs.with_context(**{self._CLEANUP_CONTEXT_KEY: True}).unlink()

        return count

    def _is_cleanup_authorized(self) -> bool:
        if not self.env.context.get(self._CLEANUP_CONTEXT_KEY):
            return False
        if not self.env.su:
            _logger.warning(
                "Audit log cleanup bypass attempted without sudo (uid=%s).",
                self.env.uid,
            )
            return False
        return True
