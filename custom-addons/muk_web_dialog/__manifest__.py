{
    'name': 'MuK Dialog', 
    'summary': 'Adds options for the dialogs',
    'description': '''
        This module adds an option to dialogs to expand it to full screen mode.
        Each user can the initial state of the dialogs in their preferences.
    ''',
    'version': '19.0.1.0.1',
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://youtu.be/QCSJugQC-O4',
    'contributors': [
        'Mathias Markl <mathias.markl@mukit.at>',
    ],
    'depends': [
        'web',
    ],
    'data': [
        'views/res_users.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            (
                'after', 
                'web/static/src/scss/primary_variables.scss', 
                'muk_web_dialog/static/src/scss/variables.scss'
            ),
        ],
        'web.assets_backend': [
            (
                'after',
                'web/static/src/core/dialog/dialog.js',
                '/muk_web_dialog/static/src/core/dialog/dialog.js',
            ),
            (
                'after',
                'web/static/src/core/dialog/dialog.scss',
                '/muk_web_dialog/static/src/core/dialog/dialog.scss',
            ),
            (
                'after',
                'web/static/src/core/dialog/dialog.xml',
                '/muk_web_dialog/static/src/core/dialog/dialog.xml',
            ),
            (
                'after',
                'web/static/src/views/view_dialogs/select_create_dialog.js',
                '/muk_web_dialog/static/src/views/view_dialogs/select_create_dialog.js',
            ),
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
