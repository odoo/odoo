import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResUsersLog(models.Model):
    _name = "res.users.log"
    _order = "id desc"
    _description = "Users Log"
    # Uses the magical fields `create_uid` and `create_date` for recording logins.
    # See `mail.presence` for more recent activity tracking purposes.

    create_uid = fields.Many2one(
        "res.users",
        string="Created by",
        readonly=True,
        index=True,
    )

    @api.autovacuum
    def _gc_user_logs(self) -> None:
        self.env.cr.execute("""
            DELETE FROM res_users_log log1 WHERE EXISTS (
                SELECT 1 FROM res_users_log log2
                WHERE log1.create_uid = log2.create_uid
                AND log1.create_date < log2.create_date
            )
        """)
        _logger.info("GC'd %d user log entries", self.env.cr.rowcount)
