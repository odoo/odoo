# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tours Recorder',
    'category': 'Hidden',
    'description': """
Odoo Web tours recorder.
========================

""",
    'version': '0.1',
    'depends': ['web_tour'],
    'assets': {
        'web.assets_backend': [
            'web_tour_recorder/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'web_tour_recorder/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
