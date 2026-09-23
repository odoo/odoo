{
    "name": "Formula Reports",
    "version": "1.1",
    "category": "Hidden",
    "summary": "Reports made of lines, expressions and columns, evaluated by formula engines",
    "description": """
Formula Reports
===============

The schema of a formula report, independent of what it reports on.

* ``report.formula`` -- a report: its lines, its columns, variants of a root
  report, sections of a composite report, and the options it offers
* ``report.formula.line`` -- a line of the hierarchy, with a group-by and the
  shortcut fields that write its ``balance`` expression
* ``report.formula.expression`` -- what a line computes under a label, by one
  of the engines: ``domain``, ``aggregation``, ``external``, ``custom``
* ``report.formula.column`` and ``report.formula.external.value``
* ``report.formula.custom.handler`` -- the abstract model a report's custom
  handler inherits

The models were ``account.report*`` while ``account`` owned them, before this
module was cut out of it.  ``account``
depends on this module and adds the ledger to each model -- the ``tax_tags`` and
``account_codes`` engines, the tax-tag lifecycle, carryover, the ledger filters.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "security/ir.access.csv",
        "data/pdf_export_templates.xml",
    ],
    "assets": {
        "report_formula.assets_pdf_export": [
            (
                "include",
                "web._assets_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            (
                "include",
                "web._assets_bootstrap_backend",
            ),
            "web/static/fonts/fonts.scss",
            "web/static/src/webclient/actions/reports/report_paged_media.css",
            "report_formula/static/src/scss/pdf_export_template.scss",
        ],
        "web.report_assets_common": [
            "report_formula/static/src/scss/pdf_export_template.scss",
        ],
        "web.assets_backend": [
            "report_formula/static/src/components/**/*",
            "report_formula/static/src/js/**/*",
        ],
        "web.assets_unit_tests": [
            "report_formula/static/tests/**/*",
        ],
    },
    "esm": {
        "bundles": [
            "report_formula.assets_pdf_export",
        ],
    },
    "pre_init_hook": "_pre_init_rename_account_report_models",
}
