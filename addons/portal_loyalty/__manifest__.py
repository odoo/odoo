# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portal Loyalty',
    'category': 'Hidden',
    'version': '1.0',
    'description': "",
    'depends': [
        'portal',
        'loyalty',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'portal_loyalty/static/src/xml/portal_loyalty_modal.xml',
            'portal_loyalty/static/src/js/portal_loyalty.js',
        ],
    },
    'license': 'LGPL-3',
}
