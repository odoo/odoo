# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tutorials',
    'category': 'Hidden',
    'description': """
Odoo Web tutorials.
===================

A tutorial describes the views an app is discovered through and, for each of
them, the fields and actions to use, with their help. The users are guided
through them view by view, at their own pace and in their own order.
""",
    'depends': ['web', 'web_tour'],
    'data': [
        'security/ir.access.csv',
        'views/web_tutorial_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'web_tutorial/static/src/**/*',
            ('remove', 'web_tutorial/static/src/tutorial/**/*'),
        ],
        'web.assets_unit_tests': [
            ('include', 'web_tutorial.tutorial'),
            'web_tutorial/static/tests/*.test.js',
        ],
        'web_tutorial.tutorial': [
            'web/static/lib/hoot-dom/**/*',
            'web_tour/static/src/tour_interactive/tour_interactive_observer.js',
            'web_tutorial/static/src/tutorial/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
