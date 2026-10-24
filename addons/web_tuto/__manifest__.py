# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tutorials',
    'category': 'Hidden',
    'description': """
Odoo Web tutorials.
===================

A tutorial describes the views an app is discovered through and, for each of
them, the fields and buttons to use, with their help. The users are guided
through them view by view, at their own pace and in their own order.
""",
    'depends': ['web'],
    'data': [
        'security/ir.access.csv',
        'views/web_tuto_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'web_tuto/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'web_tuto/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
