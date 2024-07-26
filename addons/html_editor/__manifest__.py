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
        'web.assets_backend': [
            'html_editor/static/src/**/*',
            'html_editor/static/lib/DOMpurify.js',
        ],
        'html_editor.jquery': [
            'web/static/lib/jquery/jquery.js',
            'web/static/src/legacy/js/libs/jquery.js',
            'html_editor/static/lib/jQuery.transfo.js',
        ],
        'web.assets_unit_tests': [
            'html_editor/static/tests/**/*',
        ],
        'web_editor.assets_media_dialog': [
            'html_editor/static/src/main/media/upload_progress_toast/**/*',
        ],
        'html_editor.assets_image_cropper': [
            'html_editor/static/lib/cropperjs/cropper.css',
            'html_editor/static/lib/cropperjs/cropper.js',
        ],
    },
    'license': 'LGPL-3'
}
