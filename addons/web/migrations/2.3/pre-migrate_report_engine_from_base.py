"""Pre-migration: the PDF half of ``ir.actions.report`` moved from ``base`` into ``web``.

``report.layout``, the six document-layout fields of ``res.company``
(``external_report_layout_id``, ``font``, ``primary_color``, ``secondary_color``,
``layout_background``, ``layout_background_image``) and the two technical
reports (``ir.model`` overview, ``ir.module.module`` reference) are now
declared by ``web``. The records stay -- the ``res_company`` columns, the
``report_layout`` table, the two report actions and their four QWeb views --
only their owner changes.

Every ``ir_model_data`` row ``base`` wrote for them is re-homed to ``web`` so
that ``web``'s reflection and data load find and update the same records
instead of creating new ones, and so that ``_process_end`` does not reap
``base``'s rows as orphans and, for the field rows, drop the columns behind
them. A row is left alone when ``web`` already owns one of the same name: the
reflection of a shared model gives every module its own ``model_res_company``
and ``field_res_company__id``, so ``base``'s copy is then just a duplicate.

The report model ``report.base.report_irmodulereference`` is named after the
template it renders, and the template's key is now ``web.report_irmodulereference``;
``rename_model`` rewrites the registry rows and the xml id names, and the
re-home then moves those names to ``web`` like the rest. ``web``'s data load
rewrites ``report_name``, ``report_file``, the view keys and the ``t-call``
references itself: the four views and two actions are plain (non-``noupdate``)
records that ``web`` now ships under the same xml id names.
"""

import logging

from odoo.tools.module_data import rename_model

_logger = logging.getLogger(__name__)

OLD_REPORT_MODEL = "report.base.report_irmodulereference"
NEW_REPORT_MODEL = "report.web.report_irmodulereference"

XMLID_PATTERNS = (
    "model_report_layout",
    "field_report_layout__%",
    "constraint_report_layout_%",
    "access_report_layout",
    "access_report_layout_system",
    "field_res_company__external_report_layout_id",
    "field_res_company__font",
    "field_res_company__primary_color",
    "field_res_company__secondary_color",
    "field_res_company__layout_background",
    "field_res_company__layout_background_image",
    "selection__res_company__font__%",
    "selection__res_company__layout_background__%",
    "model_report_web_report_irmodulereference",
    "field_report_web_report_irmodulereference__%",
    "report_ir_model_overview",
    "ir_module_reference_print",
    "report_irmodeloverview",
    "report_irmodeloverview_document",
    "report_irmodulereference",
    "report_irmodulereference_document",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT 1 FROM ir_model WHERE model = %s", (OLD_REPORT_MODEL,))
    if cr.fetchone():
        rename_model(cr, OLD_REPORT_MODEL, NEW_REPORT_MODEL)
    moved = 0
    for pattern in XMLID_PATTERNS:
        cr.execute(
            """
                UPDATE ir_model_data d SET module = 'web'
                 WHERE d.module = 'base'
                   AND d.name LIKE %s
                   AND NOT EXISTS (
                       SELECT 1 FROM ir_model_data e
                        WHERE e.module = 'web' AND e.name = d.name
                   )
            """,
            (pattern,),
        )
        moved += cr.rowcount
    _logger.info("web 2.3: %d report-engine xml id(s) re-homed from base", moved)
