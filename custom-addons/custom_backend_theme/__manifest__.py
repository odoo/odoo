{
    "name": "Backend Theme",
    "version": "1.0",
    "summary": "Custom styles for APIS",
    "description": "Adds custom styles to the APIS user interface.",
    "category": "Themes/Backend",
    'website': 'https://ultrasoft.mk',
    'author': 'Ultrasoft Systems',
    "depends": ["base", "web"],
    "data": [
    ],
    'assets': {
        'web.assets_backend': [
            "custom_backend_theme/static/src/css/custom.css",
        ],
        'web.assets_frontend': [
            "custom_backend_theme/static/src/css/login.css",
        ],
    },
    "installable": True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
