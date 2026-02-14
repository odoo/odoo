{
    'name': "NorTK Theme",
    'summary': "NorTK Theme: Enables a dark color scheme for the backend interface",
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'author': "Iván Chavero",
    'auto_install': True,
    'depends': ['base', 'web'],
    'data': [],
    'assets': {
        # 'web.assets_backend' is the main bundle for the Odoo interface
        'web.assets_backend': [
            'nortk_theme/static/src/scss/nortk.scss',
        ],
        # Frontend (Login, Database Selector, Website)
        'web.assets_frontend': [
            'nortk_theme/static/src/scss/nortk.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
