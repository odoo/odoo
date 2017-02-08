# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Portal',
    'category': 'Website',
    'summary': 'Account Management Frontend for your Customers',
    'version': '1.0',
    'description': """
Allows your customers to manage their account from a beautiful web interface.
        """,
    'depends': [
        'website', 'portal'
    ],
    'data': [
        'views/website_portal_templates.xml',
        'wizard/portal_wizard_views.xml',
        'data/website_portal_data.xml',
    ],
}
