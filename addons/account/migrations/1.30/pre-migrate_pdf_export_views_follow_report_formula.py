from odoo import SUPERUSER_ID, api
from odoo.tools import convert_file

MOVED_VIEWS = (
    "pdf_export_main",
    "company_information",
    "pdf_export_filters",
    "pdf_export_filter_extra_options_template",
    "pdf_export_main_table_header",
    "pdf_export_main_table_body",
    "pdf_export_cell",
)


def migrate(cr, version):
    if not version:
        return
    # The seven views changed owner. Re-home their xmlids instead of letting
    # account's _process_end delete them: every extension view, the primary
    # copies of other modules included, hangs off these records.
    cr.execute(
        """
        UPDATE ir_model_data d
           SET module = 'report_formula'
         WHERE d.module = 'account'
           AND d.model = 'ir.ui.view'
           AND d.name = ANY(%s)
           AND NOT EXISTS (
                   SELECT 1
                     FROM ir_model_data t
                    WHERE t.module = 'report_formula'
                      AND t.name = d.name
               )
        """,
        [list(MOVED_VIEWS)],
    )
    # report_formula is an installed dependency that `-u account` does not
    # reload, so nothing else would give the re-homed views their new arch,
    # whose t-call defaults name report_formula.
    convert_file(
        api.Environment(cr, SUPERUSER_ID, {}),
        "report_formula",
        "data/pdf_export_templates.xml",
        None,
        mode="update",
    )
