{
    'name': 'HBS',
    'description': 'A custom theme for Odoo',
    'version': '1.0',
    'author': 'Sanjay Sharma',
    'category': 'Theme/Creative',
    'depends': ['website'],
    'data': [
        'views/snippets/s_sidegrid.xml',
        # 'views/footer.xml',
        # 'views/header.xml',
    ],

    'images': [
        'static/description/theme_hbs.jpg',
        # 'static/description/pexels-pixabay-433989.jpg', # any screenshot of website so created can act as a preview
    ],
    'images_preview_theme': {
        # List of images changed in the theme: urls of the images
    },
    'configurator_snippets': {
        'homepage': ['s_sidegrid'],
    },
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
