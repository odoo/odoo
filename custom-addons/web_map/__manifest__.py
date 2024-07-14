# -*- coding: utf-8 -*-
{
    'name':"Map View",
    'summary':"Defines the map view for odoo enterprise",
    'description':"Allows the viewing of records on a map",
    'category': 'Hidden',
    'version':'1.0',
    'depends':['web', 'base_setup'],
    'data':[
        "views/res_config_settings.xml",
        "views/res_partner_views.xml",
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'web_map/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'web_map/static/lib/**/*',
            'web_map/static/tests/**/*',
            ('remove', 'web_map/static/tests/map_view/map_view_mobile_tests.js'),
        ],
        'web.qunit_mobile_suite_tests': [
            'web_map/static/tests/map_view/map_view_mobile_tests.js',
            'web_map/static/lib/**/*',
        ],
    }
}
