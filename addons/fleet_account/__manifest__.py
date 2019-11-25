# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Fleet - Account',
    'version': '1.0',
    'sequence': 165,
    'category': 'Human Resources/Fleet',
    'website': 'https://www.odoo.com/page/fleet',
    'summary': 'Manage your accounting for fleet',
    'depends': [
        'fleet',
        'account',
    ],
    'data': [
        'views/fleet_views.xml',
    ],
    'application': False,
}
