# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Adyen for Platforms',
    'version': '1.0',
    'category': '',
    'summary': 'Base Module for Adyen for Platforms',
    'description': 'Base Module for Adyen for Platforms, used in eCommerce and PoS',
    'depends': ['mail', 'web'],
    'data': [
        'data/adyen_platforms_data.xml',
        'security/ir.model.access.csv',
        'views/adyen_account_templates.xml',
        'views/adyen_account_views.xml',
        'views/adyen_transaction_views.xml',
        ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            # inside .
            'adyen_platforms/static/src/js/adyen_account_fields.js',
            # inside .
            'adyen_platforms/static/src/js/adyen_account_views.js',
            # inside .
            'adyen_platforms/static/src/js/adyen_transactions.js',
        ],
        'web.assets_qweb': [
            "adyen_platforms/static/src/xml/adyen_account_templates.xml",
            "adyen_platforms/static/src/xml/adyen_transactions_templates.xml",
        ],
    }
}
