# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Custom Title and Favicon',
    'version': '16.0.0',
    'sequence': 1,
    'summary': """
        Custom Title and Favicon
    """,
    'description': "",
    'author': 'bdtask',
    'maintainer': 'bdtask',
    'price': '0.0',
    'currency': 'USD',
    'website': 'https://www.bdtask.com/',
    'license': 'LGPL-3',
    'images': [
        'static/description/banner.png'
    ],
    'depends': [
        'web'
    ],
    'data': [
        'data/demo_data.xml',
        'views/favicon.xml',
    ],
    'assets': {
        'web.assets_backend_prod_only': [
            'bdtask_custom_title_and_favicon/static/src/js/favicon.js',
        ],
    },
    'demo': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [
        
    ],
}
