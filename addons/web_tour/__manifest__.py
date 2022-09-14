# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tours',
    'category': 'Hidden',
    'description': """
Odoo Web tours.
========================

""",
    'version': '0.1',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir.rule.csv',
        'views/tour_views.xml'
    ],
    'assets': {
        'web.assets_common': [
            'web_tour/static/src/scss/**/*',
            'web_tour/static/src/js/running_tour_action_helper.js',
            'web_tour/static/src/js/tip.js',
            'web_tour/static/src/js/tour_manager.js',
            'web_tour/static/src/js/tour_service.js',
            'web_tour/static/src/js/tour_step_utils.js',
            'web_tour/static/src/js/tour_utils.js',
            '/web_tour/static/src/xml/tip.xml',
        ],
        'web.assets_backend': [
            'web_tour/static/src/debug/debug_manager.js',
            'web_tour/static/src/debug/tour_dialog_component.js',
            'web_tour/static/src/services/*.js',
            'web_tour/static/src/debug/tour_dialog_component.xml',
        ],
        'web.assets_frontend': [
            'web_tour/static/src/js/public/**/*',
        ],
        'web.qunit_suite_tests': [
            'web_tour/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
