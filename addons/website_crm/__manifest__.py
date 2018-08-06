{
    'name': 'Contact Form',
    'category': 'Website',
    'sequence': 54,
    'summary': 'Generate leads from a contact form',
    'version': '2.0',
    'description': """
Generate leads or opportunities in the CRM app from a contact form published on the Contact us page of your website. This form can be customized thanks to the *Form Builder* module (available in Odoo Enterprise).
    """,
    'depends': ['website_form', 'website_partner', 'crm'],
    'data': [
        'data/website_crm_data.xml',
        'views/website_crm_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': True,
}
