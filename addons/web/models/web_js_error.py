import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WebJsError(models.Model):
    _name = "web.js.error"
    _description = "Client-side JS Error"
    _order = "recorded_at desc"
    _log_access = False

    recorded_at = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        readonly=True,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index="btree_not_null",
        readonly=True,
        ondelete="set null",
        help="User whose session emitted the beacon; null for anonymous "
        "frontend traffic.",
    )
    phase = fields.Selection(
        selection=[
            ("pre_boot", "Pre-boot"),
            ("post_boot", "Post-boot"),
            ("unknown", "Unknown"),
        ],
        string="Boot Phase",
        readonly=True,
        help="Whether the module system had finished booting. A pre_boot "
        "failure means the loader itself did not come up, so nothing else in "
        "the client is trustworthy at that point.",
    )
    kind = fields.Selection(
        selection=[
            ("error", "Uncaught Error"),
            ("unhandledrejection", "Unhandled Rejection"),
            ("service_start", "Service Failed to Start"),
            ("asset_load_error", "Bundle Asset Failed to Load"),
            ("module_rebind", "Module Rebind"),
        ],
        index="btree",
        readonly=True,
    )
    message = fields.Char(
        size=4096,
        readonly=True,
        required=True,
        help="Capped at 4096 chars at the DB level so a writer bypassing the "
        "controller cannot bloat the row.",
    )
    cause = fields.Text(
        string="Cause Chain",
        readonly=True,
        help="Flattened ``error.cause`` chain, one 'Caused by:' segment per "
        "level. This is the field an OWL lifecycle error points at: its own "
        "message says to read `cause`, and without it the report names a "
        "failure without saying why it happened.",
    )
    stack = fields.Text(readonly=True)
    filename = fields.Char(
        string="File",
        size=500,
        readonly=True,
    )
    line = fields.Integer(readonly=True)
    col = fields.Integer(
        string="Column",
        readonly=True,
    )
    url = fields.Char(
        string="URL",
        size=500,
        readonly=True,
    )
    user_agent = fields.Char(
        size=500,
        readonly=True,
    )
    reloaded = fields.Selection(
        selection=[("reloaded", "Reloaded"), ("suppressed", "Suppressed")],
        string="Self-heal",
        readonly=True,
        help="Only set for asset_load_error: whether the loader's one-per-minute "
        "self-heal reload fired, or the guard suppressed it. Null everywhere "
        "else — an absent value must not read as 'suppressed', which would "
        "claim a reload was withheld when none was ever attempted.",
    )

    _check_cause_len = models.Constraint(
        "CHECK(cause IS NULL OR char_length(cause) <= 4096)",
        "A JS error cause chain cannot exceed 4096 characters.",
    )
    _check_stack_len = models.Constraint(
        "CHECK(stack IS NULL OR char_length(stack) <= 4096)",
        "A JS error stack cannot exceed 4096 characters.",
    )
    _check_reloaded_only_on_asset_load_error = models.Constraint(
        "CHECK(reloaded IS NULL OR kind = 'asset_load_error')",
        "The reloaded field can only be set for asset_load_error records.",
    )

    @api.model
    def _record_beacon(self, values):
        self.env.cr.execute(
            f"""
            INSERT INTO {self._table}
                (recorded_at, user_id, phase, kind, message, cause, stack,
                 filename, line, col, url, user_agent, reloaded)
            VALUES
                ((now() AT TIME ZONE 'UTC'), %(user_id)s, %(phase)s, %(kind)s,
                 %(message)s, %(cause)s, %(stack)s, %(filename)s, %(line)s,
                 %(col)s, %(url)s, %(user_agent)s, %(reloaded)s)
            """,
            {
                "user_id": values.get("user_id") or None,
                "phase": values.get("phase") or None,
                "kind": values.get("kind") or None,
                "message": values["message"],
                "cause": values.get("cause") or None,
                "stack": values.get("stack") or None,
                "filename": values.get("filename") or None,
                "line": values.get("line") or 0,
                "col": values.get("col") or 0,
                "url": values.get("url") or None,
                "user_agent": values.get("user_agent") or None,
                "reloaded": values.get("reloaded") or None,
            },
        )

    @api.model
    def _remove_old_errors(self):
        days_str = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.js_error.retention_days", "30")
        )
        try:
            days = int(days_str)
        except TypeError, ValueError:
            _logger.warning(
                "web.js_error.retention_days=%r is not an integer; skipping GC",
                days_str,
            )
            return
        if days <= 0:
            return
        self.env.cr.execute(
            "DELETE FROM web_js_error"
            " WHERE recorded_at < (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')",
            (days,),
        )
        deleted = self.env.cr.rowcount
        if deleted:
            _logger.info(
                "[js-error-gc] deleted %d rows older than %d day(s)",
                deleted,
                days,
            )
