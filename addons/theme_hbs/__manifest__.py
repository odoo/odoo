{
    'name': 'HBS',
    'description': 'A custom theme for Odoo',
    'version': '1.0',
    'author': 'Sanjay Sharma',
    'category': 'Theme/Creative',
    'depends': ['website'],
    'data': [
        'views/snippets/hbs_call_to_action.xml',
        'views/footer.xml',
        'views/header.xml',
    ],

    'images': [
        'static/description/hbs_description.jpg',
        'static/description/hbs_screenshot.jpg',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'theme_hbs/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_hbs/static/fonts/*',
            'theme_hbs/static/src/scss/font.scss',
        ],
    },
    'license': 'LGPL-3',
}
