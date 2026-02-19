{
    'name': "Gemini AI Integration",
    'summary': "Odoo Gemini AI Integration",
    'description': """ App allows the application to leverage the capabilities of the Gemini language model to generate human-like responses, providing a more natural and intuitive user experience, without installing Google Generative AI packages. """,

    'author': 'Himanjali Intelligent Automation Private Limited',
    'company': 'Himanjali Intelligent Automation Private Limited',
    'maintainer': 'Himanjali Intelligent Automation Private Limited',
    'website': "https://www.himanjali.com/",
    'version': '16.0.1.0',
    'depends': ['base', 'base_setup', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/gemini_models.xml',
        'data/mail_channel_data.xml',
        'data/user_partner_data.xml',
        'views/res_config_settings.xml',
    ],
    'images': [
        "static/description/banner.gif"
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
