# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer Portal',
    'summary': 'Customer Portal',
    'sequence': '9000',
    'category': 'Hidden',
    'description': """
Customer Portal
===============

This module adds support and base feature for a fully integrated customer
portal. It is smart and smooth.""",
    'data': [
        'views/assets.xml',
        'views/portal_templates.xml',
    ],
    'depends': ['web_routing', 'mail'],
}
