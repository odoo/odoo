# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Remote Work',
    'version': '2.0',
    'category': 'Human Resources/Remote Work',
    'depends': ['hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/res_users.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_homeworking/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_homeworking/static/tests/**/*',
        ],
        "im_livechat.assets_embed_core": [
            "hr_homeworking/static/src/core/common/**/*",
        ],
        "mail.assets_public": [
            "hr_homeworking/static/src/core/common/**/*",
        ],
        "portal.assets_chatter_helpers": [
            "hr_homeworking/static/src/core/common/**/*",
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
