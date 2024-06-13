# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "IAP / Mail",
    'summary': """Bridge between IAP and mail""",
    'description': """Bridge between IAP and mail""",
    'category': 'Hidden/Tools',
    'version': '1.0',
    'depends': [
        'iap',
        'mail',
    ],
    'installable': True,
    'auto_install': True,
    'data': [
        'data/mail_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'iap_mail/static/src/js/**/*',
            'iap_mail/static/src/scss/iap_mail.scss',
        ],
        "web.dark_mode_assets_backend": [
            'iap_mail/static/src/scss/iap_mail.dark.scss',
        ],
    },
    'license': 'LGPL-3',
}
