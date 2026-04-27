# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp-Delivery',
    'category': 'WhatsApp',
    'description': """This module integrates Delivery with WhatsApp""",
    'depends': ['stock_delivery', 'whatsapp'],
    'data': [
        'data/whatsapp_template_data.xml'
    ],
    'license': 'OEEL-1',
    'auto_install': True
}
