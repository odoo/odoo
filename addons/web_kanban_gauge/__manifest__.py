# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Gauge Widget for Kanban',
    'category': 'Hidden',
    'description': """
This widget allows to display gauges using d3 library.
""",
    'version': '1.0',
    'depends': ['web'],
    'assets' : {
        'web.assets_backend': [
            'web_kanban_gauge/static/src/**/*',
            ('remove', 'web_kanban_gauge/static/src/js/kanban_gauge.js'),
        ],
        "web.assets_backend_legacy_lazy": [
            'web_kanban_gauge/static/src/js/kanban_gauge.js',
        ],
        'web.qunit_suite_tests': [
            'web_kanban_gauge/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
