# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Mail Group",
    'summary': "Manage your mailing lists",
    'description': """
        Manage your mailing lists from Odoo.
    """,
    'version': '1.0',
    'depends': [
        'mail',
        'portal',
    ],
    'auto_install': False,
    'data': [
        'data/ir_cron_data.xml',
        'data/mail_templates.xml',
        'data/mail_template_data.xml',
        'data/res_groups.xml',
        'security/ir.model.access.csv',
        'security/mail_group_security.xml',
        'wizard/mail_group_message_reject_views.xml',
        'views/mail_group_member_views.xml',
        'views/mail_group_message_views.xml',
        'views/mail_group_moderation_views.xml',
        'views/mail_group_views.xml',
        'views/mail_group_menus.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
        'data/mail_group_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mail_group/static/src/css/mail_group.scss',
            'mail_group/static/src/js/*',
        ],
        'web.assets_backend': [
            'mail_group/static/src/css/mail_group_backend.scss',
        ],
    },
    'license': 'LGPL-3',
}
