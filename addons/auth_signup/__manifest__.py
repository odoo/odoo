# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Signup',
    'description': """
Allow users to sign up and reset their password
===============================================
    """,
    'category': 'Hidden/Tools',
    'auto_install': True,
    'depends': [
        'base_setup',
        'mail',
        'web',
    ],
    'data': [
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/auth_signup_login_templates.xml',
        'views/auth_signup_templates_email.xml',
        'views/webclient_templates.xml',
        ],
    'bootstrap': True,
    'assets': {
        'web.assets_backend': [
            'auth_signup/static/src/components/**/*',
        ],
        'web.assets_frontend': [
            'auth_signup/static/src/interactions/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
