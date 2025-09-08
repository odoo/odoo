# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Unsplash Image Library',
    'category': 'Hidden',
    'summary': 'Find free high-resolution images from Unsplash',
    'version': '1.1',
    'description': """Explore the free high-resolution image library of Unsplash.com and find images to use in Odoo. An Unsplash search bar is added to the image library modal.""",
    'depends': ['base_setup', 'html_editor'],
    'data': [
        'views/res_config_settings_view.xml',
        ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'web_unsplash/static/src/frontend/unsplash_beacon.js',
        ],
        'html_editor.assets_media_dialog': [
            'web_unsplash/static/src/media_dialog/**/*',
            'web_unsplash/static/src/unsplash_credentials/**/*',
            'web_unsplash/static/src/unsplash_error/**/*',
            'web_unsplash/static/src/unsplash_service.js',
        ],
        'web.assets_unit_tests': [
            'web_unsplash/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
