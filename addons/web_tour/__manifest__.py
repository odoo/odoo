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
        'web.assets_backend': [
            'web_tour/static/src/**/*',
            'web/static/lib/hoot-dom/**/*',
        ],
        'web.assets_frontend': [
            # tour_pointer
            'web_tour/static/src/tour_pointer/tour_pointer.xml',
            'web_tour/static/src/tour_pointer/tour_pointer.scss',
            'web_tour/static/src/tour_pointer/tour_pointer.js',
            # tour_service
            'web_tour/static/src/tour_service/tour_state.js',
            'web_tour/static/src/tour_service/tour_utils.js',
            'web_tour/static/src/tour_service/tour_service.js',
            'web_tour/static/src/tour_service/tour_compilers.js',
            'web_tour/static/src/tour_service/tour_pointer_state.js',
            # hoot-dom
            'web/static/lib/hoot-dom/hoot_dom_utils.js',
            'web/static/lib/hoot-dom/hoot-dom.js',
            'web/static/lib/hoot-dom/helpers/dom.js',
            'web/static/lib/hoot-dom/helpers/events.js',
        ],
        'web.qunit_suite_tests': [
            'web_tour/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
