import logging

from odoo import fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrActionsPath(models.Model):
    _name = "ir.actions.path"
    _description = "Action Path"
    _rec_name = "path"
    _allow_sudo_commands = False

    path = fields.Char(required=True)
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        index="btree_not_null",
        required=True,
        ondelete="cascade",
    )

    _path_unique = models.Constraint(
        "unique(path)",
        "Path to show in the URL must be unique! Please choose another one.",
    )
    _action_unique = models.Constraint(
        "unique(action_id)",
        "An action has at most one path.",
    )

    def init(self) -> None:
        self.env.cr.execute(
            SQL(
                "DELETE FROM %s p WHERE NOT EXISTS"
                " (SELECT 1 FROM %s a WHERE a.id = p.action_id)",
                SQL.identifier(self._table),
                SQL.identifier(self.env["ir.actions.actions"]._table),
            )
        )
        if self.env.cr.rowcount:
            _logger.warning(
                "%d action path(s) outlived their action and were released.",
                self.env.cr.rowcount,
            )
        self.env.cr.execute(
            SQL(
                """
                INSERT INTO %s (path, action_id)
                     SELECT path, id FROM %s WHERE path IS NOT NULL
                ON CONFLICT DO NOTHING
                """,
                SQL.identifier(self._table),
                SQL.identifier(self.env["ir.actions.actions"]._table),
            )
        )
        _debug.lifecycle("init_paths_backfilled", rows=self.env.cr.rowcount)
        self.env.cr.execute(
            SQL(
                "SELECT a.id, a.path FROM %s a"
                " LEFT JOIN %s p ON p.action_id = a.id"
                " WHERE a.path IS NOT NULL AND p.id IS NULL",
                SQL.identifier(self.env["ir.actions.actions"]._table),
                SQL.identifier(self._table),
            )
        )
        _debug.lifecycle("init_paths_checked", unbacked=self.env.cr.rowcount)
        if unbacked := self.env.cr.fetchall():
            _debug.lifecycle("init_unbacked_paths_cleared", count=len(unbacked))
            self.env.cr.execute(
                SQL(
                    "UPDATE %s SET path = NULL WHERE id IN %s",
                    SQL.identifier(self.env["ir.actions.actions"]._table),
                    tuple(action_id for action_id, __ in unbacked),
                )
            )
            _logger.warning(
                "Duplicate action paths found; the path was cleared on the "
                "actions that lost it, and they are now reachable only by id: %s",
                ", ".join(
                    f"{path!r} (action {action_id})" for action_id, path in unbacked
                ),
            )
