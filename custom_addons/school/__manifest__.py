# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'school',
    'version': '14.0.1.0.0',
    'summary': '--------------------',
    'sequence': 11,
    'description': """ORM methods""",
    'category': '',
    'depends': [
            'base',
            'contacts',
            'partner_autocomplete',
    ],
    'website': 'https://www.xyz.com',
    'data': [
        'data/respartner_data.xml',
        'data/registration_data.xml',
        'data/course_data.xml',
        'data/batch_data.xml',
        'views/course_views.xml',
        'views/respartner_views.xml',
        'views/batch_views.xml',
        'views/registration_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
