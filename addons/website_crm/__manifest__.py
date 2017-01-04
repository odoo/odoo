{
    'name': 'Contact Form',
    'category': 'Website',
    'sequence': 54,
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
        'views/website_crm_config_settings_views.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': True,
}
