# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Network Printers",
    'version': '1.0',
    'category': 'Hidden/Tools',
    'summary': "Print reports straight to the printers of the local network",
    'description': """
Send reports from the browser to the printers of the local network, without an IoT box:

* ZPL printers (Zebra label printers) print the ZPL text reports;
* ePOS printers (Epson thermal printers) print the PDF reports, as images.
""",
    'depends': ['base_report_wkhtmltox', 'web'],
    'data': [
        'security/ir.access.csv',
        'views/printer_printer_views.xml',
        'views/ir_actions_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'printer/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'printer/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
