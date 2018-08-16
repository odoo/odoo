# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoobot',
    'version': '1.0',
    'category': 'Discuss',
    'summary': 'Add Odoobot in discussions',
    'description': "",
    'website': 'https://www.odoo.com/page/discuss',
    'depends': ['mail'],
    'installable': True,
    'application': False,
    'auto_install': True,
    'data': [
        'views/assets.xml',
        'data/mailbot_data.xml',
    ],
    'qweb': [
        'views/discuss.xml',
    ],
}
