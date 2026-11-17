{
    "name": "Printer",
    "summary": "Base module to manage external printers (e.g. ePOS, ZPL)",
    "version": "0.1",
    "depends": ["base"],
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "data": [
        "views/ir_actions_report.xml",
        "views/printer_views.xml",
        "wizard/select_printers_wizard.xml",
        "security/ir.access.csv",
    ],
    'demo': [
        'demo/printers.xml'
    ],
    "assets": {
        "web.assets_backend": [
            "printer/static/src/**/*",
        ],
        'web.assets_unit_tests': [
            'printer/static/tests/unit/**/*',
        ],
        'printer.assets_tests': [
            'printer/static/tests/tours/**/*',
        ],
    },
}
