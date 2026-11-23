# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Lead Livechat Sessions',
    'category': 'Website/Website',
    'summary': 'View livechat sessions for leads',
    'version': '1.0',
    'description': """ Adds a stat button on lead form view to access their livechat sessions.""",
    'depends': ['website_crm', 'website_livechat'],
    'data': [
        'views/website_crm_lead_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
