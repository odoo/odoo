# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Resellers',
    'category': 'Sales',
    'website': 'https://www.odoo.com/page/website-builder',
    'summary': 'Publish Your Channel of Resellers',
    'version': '1.0',
    'description': """
Publish and Assign Partner
==========================
        """,
    'depends': ['base_geolocalize', 'crm', 'account',
                'website_partner', 'website_google_map', 'website_portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/crm_partner_assign_data.xml',
        'wizard/crm_forward_to_partner_view.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/website_crm_partner_assign_templates.xml',
        'report/crm_lead_report_view.xml',
        'report/crm_partner_report_view.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/crm_lead_demo.xml',
        'data/res_partner_grade_demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
