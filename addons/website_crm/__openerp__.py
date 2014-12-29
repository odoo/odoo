{
    'name': 'Contact Form',
    'category': 'Website',
    'website': 'https://www.odoo.com/page/website-builder',
    'summary': 'Create Leads From Contact Form',
    'version': '2.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_form_builder','website_partner', 'crm'],
    'data': [
        'data/website_crm_data.xml',
        'views/website_crm.xml',
    ],
    'installable': True,
    'auto_install': True,
}
