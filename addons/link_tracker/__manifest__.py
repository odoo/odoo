# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Link Tracker',
    'category': 'Marketing',
    'description': """
Shorten URLs and use them to track clicks and UTMs
""",
    'version': '1.1',
    'depends': ['utm', 'mail'],
    'data': [
        'views/link_tracker_views.xml',
        'views/utm_campaign_views.xml',
        'views/catch_defender_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'link_tracker.defender_assets': [           
            # bootstrap
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_backend'),

            # required for fa icons
            'web/static/src/libs/fontawesome/css/font-awesome.css',

            # include base files from framework
            ('include', 'web._assets_core'),

            'web/static/src/core/utils/functions.js',
            'web/static/src/core/browser/browser.js',
            'web/static/src/core/registry.js',
            'web/static/src/core/assets.js',
            'link_tracker/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
