# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tours',
    'category': 'Hidden',
    'description': """
Odoo Web tours.
========================

""",
    'depends': ['web'],
    'data': [
        'views/tour_views.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            ('include', 'web_tour.assets'),
            'web_tour/static/src/tour_pointer/tour_pointer.scss',
            'web_tour/static/src/views/**/*',
            'web_tour/static/src/widgets/**/*',
        ],
        'web.assets_frontend': [
            ('include', 'web_tour.assets'),
            'web_tour/static/src/tour_pointer/tour_pointer.scss',
        ],
        'web.assets_unit_tests': [
            ('include', 'web_tour.recorder'),
            ('include', 'web_tour.automatic'),
            ('include', 'web_tour.interactive'),
            'web_tour/static/tests/tour_models.js',
            'web_tour/static/tests/*.test.js',
        ],
        "web.assets_tests": [
            'web_tour/static/src/tour_helpers/tour_helpers.js',
            ('include', 'web_tour.automatic')
        ],
        'web_tour.common': [
            'web/static/lib/hoot-dom/**/*',
            'web_tour/static/src/tour_step.js',
        ],
        'web_tour.helpers': [
            ('include', 'web_tour.common'),
            'web_tour/static/src/tour_helpers/**/*',
        ],
        'web_tour.interactive': [
            ('include', 'web_tour.helpers'),
            'web_tour/static/src/tour_interactive/**/*',
        ],
        'web_tour.automatic': [
            ('include', 'web_tour.helpers'),
            'web_tour/static/src/tour_automatic/tour_automatic.js',
            'web_tour/static/src/tour_automatic/tour_step_automatic.js',
        ],
        'web_tour.recorder': [
            ('include', 'web_tour.common'),
            'web_tour/static/src/tour_recorder/**/*',
            'web_tour/static/src/views/**/*',
            'web_tour/static/src/widgets/**/*',
        ],
        'web_tour.assets': [
            'web_tour/static/src/tour_pointer/tour_pointer.js',
            'web_tour/static/src/tour_pointer/tour_pointer.xml',
            'web_tour/static/src/tour_helpers/tour_helpers.js',
            'web_tour/static/src/tour_state.js',
            'web_tour/static/src/tour_service.js',
            'web_tour/static/src/tour_recorder/tour_recorder_state.js',
            'web_tour/static/src/tour_utils.js',
            'web_tour/static/src/onboarding_item.xml',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
