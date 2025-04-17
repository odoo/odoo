# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Base Printer',
    'version': '1.0',
    'category': 'Hardware Printer',
    'summary': 'Manage printers without IoT Box',
    'description': """
Base Printer module to connect and manage various printers like Epson directly, without requiring an IoT Box.
""",
    'depends': ['mail'],
    'data': [
        'security/base_printer_security.xml',
        'security/ir.model.access.csv',
        'data/report_print_mail_template_data.xml',
        'views/ir_actions_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'base_printer/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'base_printer/static/src/epson_printer/utils/utils.js',
            'base_printer/static/src/epson_printer/utils/html-to-image.js',
            'base_printer/static/src/epson_printer/services/render_service.js',
            'base_printer/static/tests/unit/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo IN Pvt Ltd',
    'license': 'LGPL-3',
}
