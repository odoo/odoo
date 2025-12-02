{
    'name': 'Custom IBM Plex Arabic Font',
    'version': '1.0',
    'summary': 'Apply IBM Plex Sans Arabic font across Odoo 19 backend & website',
    'category': 'Theme/Backend',
    'depends': ['web', 'website'],
    'assets': {
        'web.assets_backend': [
            'custom_ibm_flex_font/static/src/css/custom_font.css'
        ],
        'web.assets_frontend': [
            'custom_ibm_flex_font/static/src/css/custom_font.css'
        ],
        'website.assets_editor': [
            'custom_ibm_flex_font/static/src/css/custom_font.css'
        ]
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}