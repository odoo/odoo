import logging

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ResUsersLog(models.Model):
    _name = "res.users.log"
    _order = "id desc"
    _description = "Users Log"

    create_uid = fields.Many2one(
        comodel_name="res.users",
        string="Created by",
        index=True,
        readonly=True,
        ondelete="cascade",
    )

    @api.autovacuum
    def _gc_user_logs(self) -> None:
        self.env.cr.execute("""
            DELETE FROM res_users_log log1 WHERE EXISTS (
                SELECT 1 FROM res_users_log log2
                WHERE log1.create_uid = log2.create_uid
                AND (
                    log1.create_date < log2.create_date
                    OR (log1.create_date = log2.create_date AND log1.id < log2.id)
                )
            )
        """)
        _logger.info("GC'd %d user log entries", self.env.cr.rowcount)
        _debug.lifecycle("gc_user_logs", count=self.env.cr.rowcount)
