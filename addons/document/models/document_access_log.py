from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class DocumentsAccessLog(models.Model):
    _name = "document.access.log"
    _description = "Document Access Log"
    _order = "access_date desc, id desc"
    _log_access = False

    document_id = fields.Many2one(
        comodel_name="document.document",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    action = fields.Selection(
        selection=[("view", "Viewed"), ("download", "Downloaded")],
        readonly=True,
        required=True,
    )
    access_date = fields.Datetime(
        readonly=True,
        required=True,
    )

    _document_date_idx = models.Index("(document_id, access_date DESC)")

    @api.model
    def _coalescing_window(self) -> int:
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("document.access_log_window", 3600)
        )

    @api.model
    def _log(self, documents: models.Model, partner: models.Model, action: str) -> None:
        if not documents or not partner:
            return
        window = self._coalescing_window()
        now = fields.Datetime.now()
        self.env.cr.execute(
            SQL(
                """
                INSERT INTO document_access_log
                            (document_id, partner_id, action, access_date)
                     SELECT document.id, %(partner_id)s, %(action)s, %(now)s
                       FROM UNNEST(%(document_ids)s) AS document(id)
                      WHERE NOT EXISTS (
                            SELECT 1
                              FROM document_access_log AS recent
                             WHERE recent.document_id = document.id
                               AND recent.partner_id = %(partner_id)s
                               AND recent.action = %(action)s
                               AND recent.access_date > %(cutoff)s
                            )
                """,
                partner_id=partner.id,
                action=action,
                now=now,
                document_ids=documents.ids,
                cutoff=fields.Datetime.subtract(now, seconds=window),
            )
        )
        _debug.perf.count(
            "access_logged",
            action=action,
            documents=documents,
            rows=self.env.cr.rowcount,
            window=window,
        )

    @api.model
    def _retention_days(self) -> int:
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("document.access_log_retention_days", 365)
        )

    @api.autovacuum
    def _gc_access_log(self) -> tuple:
        retention_days = self._retention_days()
        if retention_days <= 0:
            return 0, False
        limit = 10000
        expired = self.search(
            [
                (
                    "access_date",
                    "<",
                    fields.Datetime.subtract(
                        fields.Datetime.now(), days=retention_days
                    ),
                )
            ],
            limit=limit,
        )
        removed = len(expired)
        _debug.lifecycle(
            "access_log_gc", removed=removed, retention_days=retention_days
        )
        expired.unlink()
        return removed, removed == limit
