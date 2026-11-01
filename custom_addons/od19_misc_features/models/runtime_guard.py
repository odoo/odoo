# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Runtime guard snapshot model.

Stores a point-in-time snapshot of the running Odoo environment: Python
version, Odoo release, number of installed modules and the database size.

Records are created manually through the ``od19.runtime.guard.wizard`` wizard.
This is **not** a cron job; it is meant to be triggered on demand by an
administrator.
"""

import logging
import sys

from odoo import api, fields, models
from odoo.release import version_info

_logger = logging.getLogger(__name__)


class Od19RuntimeGuard(models.Model):
    _name = "od19.runtime.guard"
    _description = "OD19 Runtime Guard Snapshot"
    _order = "check_date desc"

    python_version = fields.Char(
        string="Python Version",
        readonly=True,
    )
    odoo_version = fields.Char(
        string="Odoo Version",
        readonly=True,
    )
    installed_modules_count = fields.Integer(
        string="Installed Modules",
        readonly=True,
    )
    database_size_mb = fields.Float(
        string="Database Size (MB)",
        readonly=True,
        digits=(16, 2),
    )
    check_date = fields.Datetime(
        string="Check Date",
        readonly=True,
        default=fields.Datetime.now,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Checked By",
        readonly=True,
        default=lambda self: self.env.user,
    )

    def _collect_runtime_info(self):
        """Collect runtime information and return a dict of field values.

        :rtype: dict
        """
        self.ensure_one()

        installed_count = self.env["ir.module.module"].search_count(
            [("state", "=", "installed")]
        )

        # Read-only diagnostic: PostgreSQL exposes the database size only
        # through a server-side function, so there is no ORM equivalent.
        # The query neither writes data nor commits the transaction.
        database_size_mb = 0.0
        try:
            self.env.cr.execute(
                "SELECT pg_database_size(current_database()) / 1024.0 / 1024.0"
            )
            row = self.env.cr.fetchone()
            if row and row[0] is not None:
                database_size_mb = float(row[0])
        except Exception as error:  # noqa: BLE001 - diagnostic only
            _logger.warning(
                "Runtime guard: could not read database size: %s", error
            )

        odoo_version = ".".join(str(p) for p in version_info[:3])

        return {
            "python_version": sys.version,
            "odoo_version": odoo_version,
            "installed_modules_count": installed_count,
            "database_size_mb": database_size_mb,
            "check_date": fields.Datetime.now(),
            "user_id": self.env.user.id,
        }

    @api.private
    def action_collect(self):
        """Collect runtime info and write it onto the current record.

        Server-side only: decorated with :func:`api.private` so a malformed
        RPC call (e.g. nested ids or extra positional arguments) is rejected
        with a clean ``AccessError`` instead of crashing inside ``write``.
        The wizard calls this directly through Python, which is unaffected.

        :returns: ``self``
        """
        self.ensure_one()
        values = self._collect_runtime_info()
        self.write(values)
        return self
