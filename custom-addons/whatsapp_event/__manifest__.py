# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp-Website-Events',
    'category': 'Marketing/Events',
    'description': """This module integrates website event with WhatsApp""",
    'depends': ['website_event', 'whatsapp'],
    'data': [
        'data/whatsapp_template_data.xml',
    ],
    'demo': [
        'data/event_mail_demo.xml'
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
