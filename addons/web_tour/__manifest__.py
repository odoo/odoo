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
            'web_tour/static/src/tour_pointer/**/*',
            'web_tour/static/src/tour_state.js',
            'web_tour/static/src/tour_schemas.js',
            'web_tour/static/src/tour_plugin.js',
            'web_tour/static/src/tour_automatic/tour_automatic_plugin.js',
            'web_tour/static/src/tour_interactive/tour_interactive_plugin.js',
            'web_tour/static/src/tour_interactive/onboarding_item.xml',
            'web_tour/static/src/tour_recorder/tour_recorder_state.js',
            'web_tour/static/src/tour_recorder/tour_recorder_plugin.js',
            'web_tour/static/src/tour_utils.js',
            'web_tour/static/src/views/**/*',
            'web_tour/static/src/widgets/**/*',
        ],
        'web.assets_frontend': [
            'web_tour/static/src/tour_pointer/**/*',
            'web_tour/static/src/tour_state.js',
            'web_tour/static/src/tour_schemas.js',
            'web_tour/static/src/tour_plugin.js',
            'web_tour/static/src/tour_automatic/tour_automatic_plugin.js',
            'web_tour/static/src/tour_interactive/tour_interactive_plugin.js',
            'web_tour/static/src/tour_interactive/onboarding_item.xml',
            'web_tour/static/src/tour_recorder/tour_recorder_state.js',
            'web_tour/static/src/tour_recorder/tour_recorder_plugin.js',
            'web_tour/static/src/tour_utils.js',
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
        'web_tour.tour_runner': [
            'web/static/lib/hoot-dom/**/*',
            'web_tour/static/src/tour_automatic/**/*',
            'web_tour/static/src/tour_helpers/**/*',
            'web_tour/static/src/tour_interactive/**/*',
            'web_tour/static/src/tour_pointer/**/*',
            ('remove', 'web_tour/static/src/tour_pointer/tour_pointer.scss'),
            'web_tour/static/src/tour_recorder/**/*',
            'web_tour/static/src/tour_plugin.js',
            'web_tour/static/src/tour_schemas.js',
            'web_tour/static/src/tour_state.js',
            'web_tour/static/src/tour_step.js',
            'web_tour/static/src/tour_utils.js',
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
            'web_tour/static/src/tour_interactive/tour_interactive.js',
            'web_tour/static/src/tour_interactive/tour_interactive_observer.js',
            'web_tour/static/src/tour_interactive/tour_step_interactive.js',
        ],
        'web_tour.automatic': [
            ('include', 'web_tour.helpers'),
            'web_tour/static/src/tour_automatic/tour_automatic.js',
            'web_tour/static/src/tour_automatic/tour_step_automatic.js',
        ],
        'web_tour.recorder': [
            ('include', 'web_tour.common'),
            'web_tour/static/src/tour_recorder/tour_recorder.js',
            'web_tour/static/src/tour_recorder/tour_recorder.xml',
            'web_tour/static/src/tour_recorder/tour_recorder_state.js',
            'web_tour/static/src/views/**/*',
            'web_tour/static/src/widgets/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
