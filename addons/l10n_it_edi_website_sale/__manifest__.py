# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Italy eCommerce eInvoicing",
    'version': "1.0",
    'category': 'Accounting/Localizations/Website',
    'summary': "Features for Italian eCommerce eInvoicing",
    'description': """
Contains features for Italian eCommerce eInvoicing
    """,
    'depends': ['l10n_it_edi', 'website_sale'],
    'data': [
        'views/templates.xml',
        'data/data.xml'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_frontend': [
            '/l10n_it_edi_website_sale/static/src/js/l10n_it_edi_website_sale.js',
        ],
        'web.assets_tests': [
            'l10n_it_edi_website_sale/static/tests/**/*',
        ],
    },
}
