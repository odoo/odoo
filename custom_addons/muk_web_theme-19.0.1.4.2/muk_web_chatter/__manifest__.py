{
    'name': 'MuK Chatter', 
    'summary': 'Adds options for the chatter',
    'description': '''
        This module improves the design of the chatter and adds a user
        preference to set the position of the chatter in the form view.
    ''',
    'version': '19.0.1.4.2',
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://youtu.be/6oiPpkwfvdA',
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
            'muk_web_chatter/static/src/core/**/*.*',
            'muk_web_chatter/static/src/chatter/*.scss',
            'muk_web_chatter/static/src/chatter/*.xml',
            (
                'after', 
                'mail/static/src/chatter/web_portal/chatter.js', 
                'muk_web_chatter/static/src/chatter/chatter.js'
            ),
            (
                'after',
                'mail/static/src/core/common/composer.js',
                'muk_web_chatter/static/src/chatter/composer.js'
            ),
            (
                'after',
                'mail/static/src/core/common/store_service.js',
                'muk_web_chatter/static/src/chatter/store_service.js'
            ),
            (
                'after', 
                'mail/static/src/chatter/web/form_compiler.js', 
                'muk_web_chatter/static/src/views/form/form_compiler.js'
            ),
            'muk_web_chatter/static/src/views/form/form_renderer.js',
        ],
        'web.assets_unit_tests': [
            'muk_web_chatter/static/tests/**/*.test.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
