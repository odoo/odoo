{
    "name": "Test - Formula Reports",
    "version": "19.0.1.0.0",
    "category": "Hidden/Tests",
    "summary": "A formula report over a model that is not the ledger, run without account",
    "description": """
Test - Formula Reports
======================

``report_formula`` was cut out of ``account``, and the claim that it no longer
needs it can only be tested where ``account`` is absent: this module depends on
``report_formula`` and its spreadsheet glue only, declares a small model of dated
amounts, and runs the options, the evaluator, the line builder, the exports and
the spreadsheet function over it. Install it on a database that does not have ``account``:
its first test asserts that.
    """,
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "report_formula",
        "spreadsheet_report_formula",
    ],
    "data": [
        "security/ir.access.csv",
    ],
}
