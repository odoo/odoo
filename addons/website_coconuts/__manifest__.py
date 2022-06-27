{
    'name': 'Coconuts Theme',
    'summary': '',
    'description': '',
    'category': 'Website/Theme',
    'version': '15.0.0',
    'depends': ['website'],
    'license': 'OEEL-1',
    'data': [
        # Images
        'data/images.xml',
        'data/shapes.xml',
        # Pages
        'data/pages/home.xml',
        # Snippets
        'views/snippets/options.xml',
        'views/snippets/s_coconuts_boxes.xml',
        'views/snippets/s_coconuts_image_text.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'website_coconuts/static/src/scss/primary_variables.scss',
        ],
        'web._assets_frontend_helpers': [
            ('prepend', 'website_coconuts/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_frontend': [
            # Snippets
            'website_coconuts/static/src/snippets/options.scss',
            'website_coconuts/static/src/snippets/s_coconuts_boxes/000.scss',
        ],
    },
}
