# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Printer',
    'category': 'Administration/Printer',
    'summary': 'Bridge module for direct printing via local printer service',
    'description': """
Printer Integration
===================

This module provides a bridge between Odoo and a local printer application,
enabling direct printing of reports without manual downloads.

It allows users to select printers and send print jobs seamlessly. The local
application handles communication with the physical printers.

Key Features:
-------------
- Direct printing of reports from Odoo
- Integration with a local printer proxy application
- Support for multiple printer types:
    * Office Printers (PDF reports)

Printer application release link: https://github.com/odoo/epos-proxy/releases/latest
""",
    'data': [
        'security/ir.model.access.csv',
        'security/printer_security.xml',
        'views/printer.xml',
        'wizard/select_printer_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'printer/static/src/**/*',
        ],
    },
    'depends': ['base', 'web'],
    'author': 'Odoo India Pvt Ltd',
    'license': 'LGPL-3',
}
