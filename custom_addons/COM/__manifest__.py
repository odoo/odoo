# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'COM',
    'version': '14.0.1.0.0',
    'summary': '--------------------',
    'sequence': 11,
    'description': """Common ORM methods""",
    'category': '',
    'depends': [
            'base',
            'contacts',
    ],
    'website': 'https://www.xyz.com',
    'data': [
        # 'views/course_views.xml',
        'views/com_views.xml',
        # 'views/respartner_views.xml',
        # 'views/batch_views.xml',
        # 'views/registration_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
