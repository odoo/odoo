{
    'name': 'MuK Liquid Glass',
    'summary': 'Glassmorphism (liquid glass) styling on top of the MuK backend theme',
    'description': """
        Adds a frosted-glass ("liquid glass") look to the Odoo backend:
        a soft gradient backdrop with translucent, blurred chrome
        (navbar, apps sidebar, control panel, dialogs and dropdowns).
        Layers on top of muk_web_theme.
    """,
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'license': 'LGPL-3',
    'author': 'Local Dev',
    'depends': [
        'muk_web_theme',
    ],
    'assets': {
        'web.assets_backend': [
            'muk_web_liquid_glass/static/src/scss/liquid_glass.scss',
        ],
    },
    'installable': False,
    'application': False,
    'auto_install': False,
}
