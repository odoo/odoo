# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Editor',
    'category': 'Hidden',
    'description': """
Odoo Web Editor widget.
==========================

""",
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'data/editor_assets.xml',
        'views/editor.xml',
        'views/snippets.xml',
    ],
    'assets': {

        #----------------------------------------------------------------------
        # MAIN BUNDLES
        #----------------------------------------------------------------------

        'web.assets_qweb': [
            'web_editor/static/src/xml/*.xml',
        ],
        'web_editor.assets_wysiwyg': [

            # lib
            'web_editor/static/lib/cropperjs/cropper.css',
            'web_editor/static/lib/cropperjs/cropper.js',
            'web_editor/static/lib/jquery-cropper/jquery-cropper.js',
            'web_editor/static/lib/jQuery.transfo.js',
            'web/static/lib/nearest/jquery.nearest.js',
            'web_editor/static/lib/webgl-image-filter/webgl-image-filter.js',

            # odoo-editor
            'web_editor/static/lib/odoo-editor/src/style.css',
            'web_editor/static/lib/odoo-editor/src/OdooEditor.js',
            'web_editor/static/lib/odoo-editor/src/utils/constants.js',
            'web_editor/static/lib/odoo-editor/src/utils/sanitize.js',
            'web_editor/static/lib/odoo-editor/src/utils/serialize.js',
            'web_editor/static/lib/odoo-editor/src/utils/DOMPurify.js',
            'web_editor/static/lib/odoo-editor/src/tablepicker/TablePicker.js',
            'web_editor/static/lib/odoo-editor/src/powerbox/patienceDiff.js',
            'web_editor/static/lib/odoo-editor/src/powerbox/Powerbox.js',
            'web_editor/static/lib/odoo-editor/src/commands/align.js',
            'web_editor/static/lib/odoo-editor/src/commands/commands.js',
            'web_editor/static/lib/odoo-editor/src/commands/deleteBackward.js',
            'web_editor/static/lib/odoo-editor/src/commands/deleteForward.js',
            'web_editor/static/lib/odoo-editor/src/commands/enter.js',
            'web_editor/static/lib/odoo-editor/src/commands/shiftEnter.js',
            'web_editor/static/lib/odoo-editor/src/commands/shiftTab.js',
            'web_editor/static/lib/odoo-editor/src/commands/tab.js',
            'web_editor/static/lib/odoo-editor/src/commands/toggleList.js',

            # utils
            'web_editor/static/src/js/wysiwyg/PeerToPeer.js',

            # odoo utils
            ('include', 'web._assets_helpers'),

            'web_editor/static/src/scss/bootstrap_overridden.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            # integration
            'web_editor/static/src/scss/wysiwyg.scss',
            'web_editor/static/src/scss/wysiwyg_iframe.scss',
            'web_editor/static/src/scss/wysiwyg_snippets.scss',

            'web_editor/static/src/js/wysiwyg/fonts.js',
            'web_editor/static/src/js/base.js',
            'web_editor/static/src/js/editor/image_processing.js',
            'web_editor/static/src/js/editor/custom_colors.js',

            # widgets & plugins
            'web_editor/static/src/js/wysiwyg/widgets/**/*',
            'web_editor/static/src/js/editor/snippets.editor.js',
            'web_editor/static/src/js/editor/toolbar.js',
            'web_editor/static/src/js/editor/snippets.options.js',

            # Launcher
            'web_editor/static/src/js/wysiwyg/wysiwyg.js',
            'web_editor/static/src/js/wysiwyg/wysiwyg_iframe.js',
        ],
        'web.assets_common': [
            'web_editor/static/lib/vkbeautify/**/*',
            'web_editor/static/src/js/common/**/*',
            'web_editor/static/lib/odoo-editor/src/utils/utils.js',
        ],
        'web.assets_backend': [
            'web_editor/static/src/scss/web_editor.common.scss',
            'web_editor/static/src/scss/web_editor.backend.scss',

            'web_editor/static/src/js/wysiwyg/dialog.js',
            'web_editor/static/src/js/frontend/loader.js',
            'web_editor/static/src/js/backend/**/*',
        ],
        'web.assets_frontend_minimal': [
            'web_editor/static/src/js/frontend/loader_loading.js',
        ],
        'web.assets_frontend': [
            'web_editor/static/src/scss/web_editor.common.scss',
            'web_editor/static/src/scss/web_editor.frontend.scss',

            'web_editor/static/src/js/wysiwyg/dialog.js',
            'web_editor/static/src/js/frontend/loader.js',
        ],

        #----------------------------------------------------------------------
        # SUB BUNDLES
        #----------------------------------------------------------------------

        'web._assets_primary_variables': [
            'web_editor/static/src/scss/web_editor.variables.scss',
        ],
        'web._assets_secondary_variables': [
            'web_editor/static/src/scss/secondary_variables.scss',
        ],
        'web._assets_backend_helpers': [
            'web_editor/static/src/scss/bootstrap_overridden_backend.scss',
            'web_editor/static/src/scss/bootstrap_overridden.scss',
        ],
        'web._assets_frontend_helpers': [
            ('prepend', 'web_editor/static/src/scss/bootstrap_overridden.scss'),
        ],

        # ----------------------------------------------------------------------
        # TESTS BUNDLES
        # ----------------------------------------------------------------------

        'web.qunit_suite_tests': [
            ('include', 'web_editor.assets_wysiwyg'),

            'web_editor/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
