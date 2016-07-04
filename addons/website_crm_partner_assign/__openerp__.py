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
    'depends': ['base_geolocalize', 'crm', 'account', 'portal',
                'website_partner', 'website_google_map', 'website_portal'],
    'data': [
        'data/portal_data.xml',
        'data/crm_partner_assign_data.xml',
        'security/ir.model.access.csv',
        'wizard/crm_forward_to_partner_view.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/partner_grade.xml',
        'views/website_crm_partner_assign_templates.xml',
        'views/website_crm_portal_lead_templates.xml',
        'report/crm_lead_report_view.xml',
        'report/crm_partner_report_view.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/crm_lead_demo.xml',
        'data/res_partner_grade_demo.xml',
    ],
    'test': ['test/partner_assign.yml'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
