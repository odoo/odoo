{
    "name": "Formula Reports",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Reports made of lines, expressions and columns, evaluated by formula engines",
    "description": """
Formula Reports
===============

The schema of a formula report, independent of what it reports on.

* ``account.report`` -- a report: its lines, its columns, variants of a root
  report, sections of a composite report, and the options it offers
* ``account.report.line`` -- a line of the hierarchy, with a group-by and the
  shortcut fields that write its ``balance`` expression
* ``account.report.expression`` -- what a line computes under a label, by one
  of the engines: ``domain``, ``aggregation``, ``external``, ``custom``
* ``account.report.column`` and ``account.report.external.value``
* ``account.report.custom.handler`` -- the abstract model a report's custom
  handler inherits

The models keep the names they had in ``account``, which owned them until this
module was cut out of it: 159 data records in 97 modules and the handlers of 77
enterprise modules name them, and a rename is a separate change.  ``account``
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
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "report_formula/static/src/components/**/*",
            "report_formula/static/src/js/**/*",
        ],
        "web.assets_unit_tests": [
            "report_formula/static/tests/**/*",
        ],
    },
}
