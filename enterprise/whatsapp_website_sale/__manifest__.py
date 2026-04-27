# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp-eCommerce',
    'category': 'WhatsApp',
    'summary': 'This module integrates website sale with WhatsApp',
    'description': """This module integrates website sale with WhatsApp""",
    'depends': ['website_sale', 'whatsapp'],
    'data': [
        'views/res_config_settings_views.xml'
    ],
    'demo': [
        'data/demo.xml'
    ],
    'license': 'OEEL-1',
    'auto_install': True
}
