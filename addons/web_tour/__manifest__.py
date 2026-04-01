# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tours',
    'category': 'Hidden',
    'description': """
Odoo Web tours.
========================

""",
    'version': '1.0',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'views/tour_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'web_tour/static/src/scss/**/*',
            'web_tour/static/src/js/tour_pointer/**/*',
            'web_tour/static/src/js/utils/**/*',
            'web_tour/static/src/js/tour_state.js',
            'web_tour/static/src/js/tour_service.js',
            'web_tour/static/src/js/tour_recorder/tour_recorder_state.js',
            'web_tour/static/src/tour_utils.js',
            'web_tour/static/src/js/onboarding_item.xml',
            'web_tour/static/src/views/**/*',
            'web_tour/static/src/widgets/**/*',
        ],
        'web.assets_frontend': [
            'web_tour/static/src/scss/**/*',
            'web_tour/static/src/js/tour_pointer/**/*',
            'web_tour/static/src/js/utils/**/*',
            'web_tour/static/src/js/tour_state.js',
            'web_tour/static/src/js/tour_service.js',
            'web_tour/static/src/js/tour_recorder/tour_recorder_state.js',
            'web_tour/static/src/tour_utils.js',
            'web_tour/static/src/js/onboarding_item.xml',
        ],
        'web.assets_unit_tests': [
            ('include', 'web_tour.recorder'),
            ('include', 'web_tour.automatic'),
            ('include', 'web_tour.interactive'),
            'web_tour/static/tests/*.test.js',
        ],
        "web.assets_tests": [
            'web_tour/static/src/js/tour_automatic/tour_helpers.js',
            ('include', 'web_tour.automatic')
        ],
        'web_tour.common': [
            'web/static/lib/hoot-dom/**/*',
            'web_tour/static/src/js/tour_step.js',
        ],
        'web_tour.interactive': [
            ('include', 'web_tour.common'),
            'web_tour/static/src/js/tour_interactive/**/*',
        ],
        'web_tour.automatic': [
            ('include', 'web_tour.common'),
            'web_tour/static/src/js/tour_automatic/**/*',
        ],
        'web_tour.recorder': [
            ('include', 'web_tour.common'),
            'web_tour/static/src/js/tour_recorder/**/*',
            'web_tour/static/src/views/**/*',
            'web_tour/static/src/widgets/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
