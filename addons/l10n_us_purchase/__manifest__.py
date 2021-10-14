# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'l10n_us_purchase',
    'version': '1.0',
    'category': 'Accounting/Localizations/Purchase',
    'description': """l10n_us_purchase""",
    'depends': [
        'l10n_us',
        'purchase'
    ],
    'data': [
        'views/l10n_us_purchase_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_us_purchase/static/src/js/l10n_us_purchase_portal.js',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
