# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on sale orders',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add sale order UTM info on mass mailing',
    'description': """UTM and mass mailing on sale orders""",
    'depends': ['sale', 'mass_mailing'],
    'data': [
        'views/mailing_mailing_views.xml',
    ],
    'demo': [
        'demo/mailing_mailing.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
