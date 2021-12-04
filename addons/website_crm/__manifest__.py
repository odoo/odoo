# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Contact Form',
    'category': 'Website/Website',
    'sequence': 54,
    'summary': 'Generate leads from a contact form',
    'version': '2.1',
    'description': """
Generate leads or opportunities in the CRM app from a contact form published on the Contact us page of your website.
This form can be customized thanks to the *Form Builder* module (available in Odoo Enterprise).

This module includes contact phone and mobile numbers validation.""",
    'depends': ['website_form', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'data/website_crm_data.xml',
        'views/website_crm_lead_views.xml',
        'views/website_crm_templates.xml',
        'views/res_config_settings_views.xml',
        'views/website_visitor_views.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
