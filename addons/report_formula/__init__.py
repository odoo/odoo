from odoo.db.schema import table_exists
from odoo.tools import SQL
from odoo.tools.module_data import rename_model

from . import controllers
from . import models

RENAMED_MODELS = (
    ("account.report", "report.formula"),
    ("account.report.line", "report.formula.line"),
    ("account.report.expression", "report.formula.expression"),
    ("account.report.column", "report.formula.column"),
    ("account.report.external.value", "report.formula.external.value"),
    ("account.report.custom.handler", "report.formula.custom.handler"),
)


RENAMED_RELATIONS = (("account_report_section_rel", "report_formula_section_rel"),)


def rename_account_report_models(cr):
    for old, new in RENAMED_MODELS:
        rename_model(cr, old, new)
    # rename_model follows only the join tables named by default; the sections'
    # is named explicitly, so it is moved here with its registry rows
    for old, new in RENAMED_RELATIONS:
        if table_exists(cr, old) and not table_exists(cr, new):
            cr.execute(
                SQL(
                    "ALTER TABLE %s RENAME TO %s",
                    SQL.identifier(old),
                    SQL.identifier(new),
                )
            )
        cr.execute(
            SQL(
                "UPDATE ir_model_fields SET relation_table = %s WHERE relation_table = %s",
                new,
                old,
            )
        )
        cr.execute(
            SQL("UPDATE ir_model_relation SET name = %s WHERE name = %s", new, old)
        )


ADOPTED_VIEWS = (
    "pdf_export_main",
    "company_information",
    "pdf_export_filters",
    "pdf_export_filter_extra_options_template",
    "pdf_export_main_table_header",
    "pdf_export_main_table_body",
    "pdf_export_cell",
)


def _pre_init_rename_account_report_models(env):
    # A database from before report_formula existed installs it fresh, and an
    # install runs no migration: the account_report tables account used to own
    # are renamed here, before this module creates its own; and the PDF export
    # views account used to own become this module's before its data loads, so
    # the load updates them instead of creating copies that account's upgrade
    # would then delete the originals of.
    rename_account_report_models(env.cr)
    env.cr.execute(
        SQL(
            """
            UPDATE ir_model_data
               SET module = 'report_formula'
             WHERE module = 'account'
               AND model = 'ir.ui.view'
               AND name = ANY(%s)
            """,
            list(ADOPTED_VIEWS),
        )
    )
