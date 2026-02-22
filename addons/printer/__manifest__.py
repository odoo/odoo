{
    'name': "Printer",
    'summary': "Base module to manage external printers (e.g. ePOS, ZPL)",
    'version': '0.1',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_actions_report.xml',
        'views/printer_views.xml',
        'wizard/select_printers_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'printer/static/src/**/*',
        ],
    },
}
