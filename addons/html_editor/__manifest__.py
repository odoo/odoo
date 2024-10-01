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

    'author': "odoo",
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
            ('remove', 'html_editor/static/src/components/history_dialog/history_dialog.dark.scss'),
            ('include', 'html_editor.assets_media_dialog'),
        ],
        'html_editor.assets_media_dialog': [
            # Bundle to use the media dialog in the backend and the frontend
            'html_editor/static/src/main/media/media_dialog/**/*',
            'html_editor/static/src/utils/**/*',

        ],
        "web.assets_web_dark": [
            'html_editor/static/src/components/history_dialog/history_dialog.dark.scss',
        ],
        'web.assets_unit_tests': [
            'html_editor/static/tests/**/*',
        ],
        'html_editor.assets_image_cropper': [
            'html_editor/static/lib/cropperjs/cropper.css',
            'html_editor/static/lib/cropperjs/cropper.js',
        ],
    },
    'license': 'LGPL-3'
}
