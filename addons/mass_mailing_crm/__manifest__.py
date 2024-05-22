# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on lead / opportunities',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add lead / opportunities UTM info on mass mailing',
    'description': """UTM and mass mailing on lead / opportunities""",
    'depends': ['crm', 'mass_mailing'],
    'data': [
        'views/mailing_mailing_views.xml',
    ],
    'demo': [
        'data/mass_mailing_demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
