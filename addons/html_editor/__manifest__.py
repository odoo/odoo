{
    'name': "HTML Editor",
    'summary': """
        A Html Editor component and plugin system
    """,
    'description': """
Html Editor
==========================
This addon provides an extensible, maintainable editor.
    """,

    'website': "https://www.odoo.com",
    'version': '1.0',
    'category': 'Hidden',
    'depends': ['base', 'bus', 'web'],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            ('include', 'html_editor.assets_media_dialog')
        ],
        'web.assets_backend': [
            'html_editor/static/src/**/*',
            ('include', 'html_editor.assets_media_dialog'),
            ('include', 'html_editor.assets_link_popover'),
            ('remove', 'html_editor/static/src/components/history_dialog/history_dialog.dark.scss'),
            ('remove', 'html_editor/static/src/main/toolbar/toolbar.dark.scss'),
        ],
        'html_editor.assets_media_dialog': [
            # Bundle to use the media dialog in the backend and the frontend
            'html_editor/static/src/main/media/media_dialog/**/*',
            'html_editor/static/src/utils/**/*',

        ],
        "web.assets_web_dark": [
            'html_editor/static/src/components/history_dialog/history_dialog.dark.scss',
            'html_editor/static/src/main/toolbar/toolbar.dark.scss',
        ],
        'web.assets_unit_tests': [
            'html_editor/static/tests/**/*',
        ],
        'html_editor.assets_image_cropper': [
            'html_editor/static/lib/cropperjs/cropper.css',
            'html_editor/static/lib/cropperjs/cropper.js',
        ],
        'html_editor.assets_link_popover': [
            'html_editor/static/src/main/link/link_popover.js',
            'html_editor/static/src/main/link/link_popover.xml',
            'html_editor/static/src/main/link/utils.js',
        ],
    },
    'license': 'LGPL-3'
}
