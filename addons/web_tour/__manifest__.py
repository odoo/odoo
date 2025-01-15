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
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'web_tour/static/src/**/*',
            'web/static/lib/hoot-dom/**/*',
        ],
        'web.assets_frontend': [
            'web_tour/static/src/tour_pointer/**/*',
            'web_tour/static/src/tour_service/**/*',
            'web/static/lib/hoot-dom/**/*',
        ],
        'web.assets_unit_tests': [
            # TODO: PIPU/JUM must be reactivated when Script timeout exceeded due to Hoot is fixed.
            # 'web_tour/static/tests/tour_automatic.test.js',
            'web_tour/static/tests/tour_interactive.test.js',
            'web_tour/static/tests/tour_recorder.test.js',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
