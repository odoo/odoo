# -*- coding: utf-8 -*-
##############################################################################
#
#    Part of cube48.de. See LICENSE file for full copyright and licensing details.
#
##############################################################################
{
    'name': "Toggle Debug Mode",

    'summary': """
        Toggle to debug mode in the top right user menu, just one click!""",

    'description': """
        Toggle to debug mode in the top right user menu, just one click!

    """,

    'author': "cube48 AG",
    'website': "https://www.cube48.de",
    'category': 'Tools',
    'version': '16.0.0.1',
    'depends': [
        'base',
    ],
    'assets': {
        'web.assets_backend': [
            'toggle_developer_mode/static/src/css/app.css',
            'toggle_developer_mode/static/src/js/debug_mode_js.js',
        ],
    },
    'images': ["static/description/banner.png"],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
}
