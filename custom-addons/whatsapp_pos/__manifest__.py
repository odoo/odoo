# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp-POS',
    'category': 'WhatsApp',
    'description': """This module integrates POS with WhatsApp""",
    'depends': ['point_of_sale', 'whatsapp'],
    'data': [
        'data/whatsapp_template_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'data/point_of_sale_demo.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'whatsapp_pos/static/src/js/**/*',
            'whatsapp_pos/static/src/xml/**/*',
            ('after', 'point_of_sale/static/src/scss/pos.scss', 'whatsapp_pos/static/src/scss/whatsapp_pos.scss'),
        ],
    },
    'license': 'OEEL-1',
    'auto_install': True
}
