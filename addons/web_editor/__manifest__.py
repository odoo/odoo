# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Editor',
    'category': 'Hidden',
    'description': """
Odoo Web Editor widget.
==========================

""",
    'depends': ['bus', 'web', 'html_editor'],
    'data': [
        'data/editor_assets.xml',
        'views/editor.xml',
        'views/snippets.xml',
    ],
    'assets': {

        #----------------------------------------------------------------------
        # MAIN BUNDLES
        #----------------------------------------------------------------------

        'web_editor.assets_snippets_menu': [
            'web_editor/static/src/js/core/owl_utils.js',
            'web_editor/static/src/js/editor/snippets.editor.js',
            'web_editor/static/src/js/editor/snippets.options.js',
        ],
        'web_editor.assets_media_dialog': [
            'web_editor/static/src/components/**/*',
        ],

        # ----------------------------------------------------------------------
        # TESTS BUNDLES
        # ----------------------------------------------------------------------

        'web.qunit_suite_tests': [
            ('include', 'web_editor.assets_snippets_menu'),

            'web_editor/static/tests/**/*',
            'web_editor/static/src/js/editor/odoo-editor/test/utils.js'
        ],
        'web_editor.mocha_tests': [
            'web/static/src/module_loader.js',
            # insert module dependencies here
            'web/static/src/core/utils/concurrency.js',

            'web_editor/static/src/js/editor/odoo-editor/src/**/*js',
            'web_editor/static/src/js/editor/odoo-editor/test/spec/*js',
            'web_editor/static/src/js/editor/odoo-editor/test/*js',

            'web/static/lib/dompurify/DOMpurify.js',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
