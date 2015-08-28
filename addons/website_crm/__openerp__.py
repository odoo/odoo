# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Contact Form',
    'category': 'Website',
    'website': 'https://www.odoo.com/page/website-builder',
    'summary': 'Create Leads From Contact Form',
    'version': '2.0',
    'description': """
Odoo Contact Form
====================

        """,
    'depends': ['website_form', 'website_partner', 'crm'],
    'data': [
        'data/website_crm_data.xml',
        'views/website_crm_templates.xml',
    ],
    'auto_install': True,
}
