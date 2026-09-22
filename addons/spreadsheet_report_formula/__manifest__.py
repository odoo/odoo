{
    "name": "Spreadsheet Formula Reports",
    "version": "1.0",
    "category": "Hidden",
    "summary": "The ODOO.REPORT spreadsheet function: a formula report's figure in a cell",
    "description": """
Spreadsheet Formula Reports
===========================

``ODOO.REPORT(report, line_code, column, period)`` returns the figure a formula
report shows for one line and one column over a period, computed by the report
engine itself: a dashboard cell and the report agree by construction, instead of
the cell re-deriving the line from account prefixes.
    """,
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "report_formula",
        "spreadsheet",
    ],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            (
                "after",
                "spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js",
                "spreadsheet_report_formula/static/src/**/*.js",
            ),
        ],
        "web.assets_unit_tests": [
            "spreadsheet_report_formula/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
