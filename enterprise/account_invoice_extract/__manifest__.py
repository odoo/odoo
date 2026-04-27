# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Invoice Extract',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Extract data from invoice scans to fill them automatically',
    'depends': ['account_extract'],
    'data': [
        'security/ir.model.access.csv',
        'data/crons.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_invoice_extract/static/src/js/*.js',
            'account_invoice_extract/static/src/css/*.css',
            'account_invoice_extract/static/src/xml/*.xml',
        ],
        'web.assets_unit_tests': [
            'account_invoice_extract/static/src/tests/**/*',
        ],
    }
}
