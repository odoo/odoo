{
    'name': 'Hide Or Show Password',
    'version': '15.0.1.0.0',
    'summary': """
        Show and Hide fields by typing a password, login form, signup form, user change password
    """,
    'author': 'Newbie Dev',
    'website': 'https://agvenmuharisrifqi.github.io',
    'license': 'AGPL-3',
    'category': 'Custom/Custom',
    'depends': [
        'web', 'base', 'auth_signup'
    ],
    'data': [
        'views/login_signup.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hide_or_show_password/static/src/css/password_eye.scss',
            'hide_or_show_password/static/src/js/password_eye.js',
            'hide_or_show_password/static/src/js/profile.js',
        ],
        'web.assets_frontend': [
            'hide_or_show_password/static/src/css/login_signup.scss',
            'hide_or_show_password/static/src/js/login_signup.js',
        ],
        'web.assets_qweb': [
            'hide_or_show_password/static/src/xml/profile.xml',
        ],
    },
    'installable': True,
    'images':  ['static/description/banner.png'],
}