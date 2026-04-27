# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp-Website-Events',
    'category': 'Marketing/Events',
    'description': """This module integrates website event with WhatsApp""",
    'depends': ['event', 'whatsapp'],
    'data': [
        'data/whatsapp_template_data.xml',
    ],
    'demo': [
        'data/event_mail_demo.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_event/static/src/template_reference_field/field_event_mail_template_reference.xml',
        ],
    },
    'license': 'OEEL-1',
    'auto_install': True,
}
