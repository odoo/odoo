{
    "name": "Backend Theme",
    "version": "1.0",
    "summary": "Custom styles for APIS",
    "description": "Adds custom styles to the APIS user interface.",
    "category": "Themes/Backend",
    'website': 'https://ultrasoft.mk',
    'author': 'Ultrasoft Systems',
    'depends': ['base', 'web'],
    'data': [
        "views/head.xml",
    ],
    'assets': {
        'web.assets_backend': [
            "custom_backend_theme/static/src/css/custom.css",
            "custom_backend_theme/static/src/js/custom_theme.js",
        ],
        'web.assets_frontend': [
            "custom_backend_theme/static/src/css/login.css",
        ],
        'point_of_sale.assets': [
            'custom_backend_theme/static/src/xml/point_of_sale/**/*.xml',
            'custom_backend_theme/static/src/css/point_of_sale.css',
        ]
    },
    "installable": True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
