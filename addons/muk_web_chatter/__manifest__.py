{
    'name': 'MuK Chatter', 
    'summary': 'Adds options for the chatter',
    'description': '''
        This module improves the design of the chatter and adds a user
        preference to set the position of the chatter in the form view.
    ''',
    'version': '17.0.1.0.1', 
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://mukit.at/demo',
    'contributors': [
        'Mathias Markl <mathias.markl@mukit.at>',
    ],
    'depends': [
        'mail',
    ],
    'data': [
        'views/res_users.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            (
                'after', 
                'web/static/src/scss/primary_variables.scss', 
                'muk_web_chatter/static/src/scss/variables.scss'
            ),
        ],
        'web.assets_backend': [
            (
                'after', 
                'mail/static/src/views/web/form/form_compiler.js', 
                'muk_web_chatter/static/src/views/form/form_compiler.js'
            ),
            'muk_web_chatter/static/src/core/**/*.xml',
            'muk_web_chatter/static/src/core/**/*.scss',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
