# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Google Analytics',
    'version': '1.0',
    'category': 'Extra Tools',
    'complexity': "easy",
    'description': """
Google Analytics.
=================

Collects web application usage with Google Analytics.
    """,
    'website': 'https://www.odoo.com/page/website-builder',
    'depends': ['web'],
    'data': [
        'views/web_analytics.xml',
    ],
    'installable': True,
    'active': False,
}
