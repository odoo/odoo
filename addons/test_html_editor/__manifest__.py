{
    "name": "Test - HTML Editor",
    "version": "19.0.1.0.0",
    "category": "Hidden/Tests",
    "summary": "Concrete records the html_editor field converters run against",
    "description": """
Test - HTML Editor
==================

``html_editor.converter.test`` carries one field of every type the QWeb field
converters round-trip, and ``html_editor.converter.test.sub`` is the record its
Many2one points at. Both are fixtures: they exist so that ``from_html`` can be
measured against a real record rather than a mock, and they live here so that
no customer database carries their tables.
    """,
    "author": "Odoo S.A., AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "html_editor",
    ],
    "data": [
        "security/ir.access.csv",
    ],
}
