from typing import Any

from odoo import _, api, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class KpiProvider(models.AbstractModel):
    """Extend the KPI provider with document metrics."""

    _inherit = "kpi.provider"

    @api.model
    def get_documents_kpi_summary(self) -> list[dict]:
        """Return the document KPI summary."""
        return get_kpi_summary(self.env.cr, self.env.uid)

    @api.model
    def get_kpi_summary(self) -> list[dict]:
        """Return the KPI summary including document metrics."""
        result = super().get_kpi_summary()
        result.extend(self.get_documents_kpi_summary())
        return result


def get_kpi_summary(cr: Any, uid: int) -> list[dict]:
    """Retrieve the number of active documents currently present in the Inbox folder.

    Only active non-folder documents located in the configured Inbox hierarchy
    are counted.

    This function intentionally bypasses the ORM so KPI summaries can be retrieved
    without loading a registry, allowing multi-database servers to serve them faster.

    .. warning::
        The returned count is **database-wide**: it is not filtered by access
        rights, record rules, nor by company. ``uid`` is used *only* to pick the
        language for the translated label -- despite that parameter, the value
        is NOT per-user. This matches the other KPI providers (e.g. ``account``)
        and the only consumer is the SaaS ``databases`` module. Do not surface
        this value to an end user as if it were their own Inbox count.
    """
    expected_columns = {
        "document_document.id",
        "document_document.folder_id",
        "document_document.type",
        "document_document.active",
    }

    cr.execute(
        SQL(
            """
        SELECT table_name || '.' || column_name
          FROM information_schema.columns
         WHERE table_name || '.' || column_name IN %(columns)s
    """,
            columns=tuple(expected_columns),
        )
    )
    existing_columns = {x[0] for x in cr.fetchall()}
    if expected_columns - existing_columns:
        # Needed columns are not present -> module is not installed
        _debug.logic("kpi_skipped", reason="module_absent")
        return []

    cr.execute(
        SQL("""
        SELECT document.parent_path
          FROM document_document document
          JOIN ir_model_data imd ON imd.model = 'document.document'
                                AND imd.res_id = document.id
         WHERE imd.module = 'document'
           AND imd.name = 'document_inbox_folder'
           AND document.active
    """)
    )
    row = cr.fetchone()
    if not row:
        _debug.logic("kpi_skipped", reason="no_inbox_folder")
        return []
    (inbox_path,) = row

    cr.execute(
        SQL(
            """
        SELECT COUNT(*)
          FROM document_document document
         WHERE document.type != 'folder'
           AND document.parent_path LIKE (%(inbox_path)s || '%%')
           AND document.active
    """,
            inbox_path=inbox_path,
        )
    )
    (count,) = cr.fetchone()

    cr.execute(
        SQL(
            """
        SELECT partner.lang
          FROM res_users u
          JOIN res_partner partner ON u.partner_id = partner.id
         WHERE u.id = %(uid)s
         LIMIT 1
    """,
            uid=uid,
        )
    )
    row = cr.fetchone()
    context = {  # noqa: F841 "unused" `context` is actually used by `_` frame inspection
        "lang": row[0] if row else "en_US",
    }

    _debug.perf.count("kpi_inbox_counted", count=count)
    return [
        {
            "id": "document.inbox",
            "name": _("Inbox"),
            "type": "integer",
            "value": count,
        }
    ]
