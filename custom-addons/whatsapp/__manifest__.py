# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo WhatsApp Integration',
    'category': 'WhatsApp',
    'summary': 'Integrates Odoo with WhatsApp to use WhatsApp messaging service',
    'version': '1.0',
    'description': """This module integrates Odoo with WhatsApp to use WhatsApp messaging service""",
    'depends': ['mail', 'phone_validation'],
    'data': [
        'data/ir_actions_server_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_module_category_data.xml',
        'data/whatsapp_templates_preview.xml',
        'security/res_groups.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'wizard/whatsapp_preview_views.xml',
        'wizard/whatsapp_composer_views.xml',
        'views/discuss_channel_views.xml',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_template_button_views.xml',
        'views/whatsapp_template_variable_views.xml',
        'views/res_config_settings_views.xml',
        'views/whatsapp_menus.xml',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'assets': {
        'web.assets_backend': [
            'whatsapp/static/src/**/*',
            # Don't include dark mode files in light mode
            ('remove', 'whatsapp/static/src/**/*.dark.scss'),
        ],
        "web.assets_web_dark": [
            'whatsapp/static/src/**/*.dark.scss',
        ],
        'web.tests_assets': [
            'whatsapp/static/tests/helpers/**/*.js',
        ],
        'web.qunit_suite_tests': [
            'whatsapp/static/tests/**/*',
            ('remove', 'whatsapp/static/tests/helpers/**/*.js'),
        ],
    },
    'license': 'OEEL-1',
    'application': True,
    'installable': True,
}
