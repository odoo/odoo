# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp-Sale',
    'category': 'WhatsApp',
    'description': """This module integrates sale with WhatsApp""",
    'depends': ['sale', 'whatsapp'],
    'data': [
        'data/whatsapp_template_data.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True
}
