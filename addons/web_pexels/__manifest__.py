# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Pexels Image Library',
    'category': 'Hidden',
    'summary': 'The best free stock photos, royalty free images & videos shared by creators.',
    'version': '1.1',
    'description': """Explore the free high-resolution image library of Pexels.com and find images to use in Odoo.
                      An Pexels search bar is added to the image library modal.""",
    'depends': ['base_setup', 'web_editor', 'html_editor'],
    'data': [
        'views/res_config_settings_view.xml',
    ],
    'auto_install': False,
    'assets': {
        'html_editor.assets_media_dialog': [
            'web_pexels/static/src/media_dialog/**/*',
            'web_pexels/static/src/pexels_credentials/**/*',
            'web_pexels/static/src/pexels_error/**/*',
            'web_pexels/static/src/pexels_service.js',
        ],
        'web_editor.assets_media_dialog': [
            # Bundle to remove when removing web_editor
            'web_pexels/static/src/media_dialog_legacy/**/*',
            'web_pexels/static/src/pexels_credentials/**/*',
            'web_pexels/static/src/pexels_error/**/*',
            'web_pexels/static/src/pexels_service.js',
        ],
        'web.qunit_suite_tests': [
            'web_pexels/static/tests/legacy/**/*',
        ],
        'web.assets_unit_tests': [
            'web_pexels/static/tests/**/*',
            ('remove', 'web_pexels/static/tests/legacy/**/*'),
        ],
    },
    'license': 'LGPL-3',
}
