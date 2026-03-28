{
    'name': 'Avantgarde Theme',
    'description': 'Avantgarde is a sophisticated theme to inspire and impress',
    'category': 'Theme/Creative',
    'summary': 'Design, Fine Art, Artwork, Creative, Creativity, Galleries, Trends, Shows, Magazines, Blogs',
    'sequence': 150,
    'version': '2.0.0',
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/images_library.xml',
        'views/customizations.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/poster.webp',
        'static/description/avantgarde_screenshot.webp',
    ],
    'images_preview_theme': {
        'website.s_cover_default_image': '/theme_avantgarde/static/src/img/pictures/bg_image_08.webp',
        'website.library_image_13': '/theme_avantgarde/static/src/img/pictures/library_image_13.webp',
        'website.library_image_03': '/theme_avantgarde/static/src/img/pictures/library_image_03.webp',
        'website.library_image_16': '/theme_avantgarde/static/src/img/pictures/library_image_16.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_sidegrid', 's_features_wall', 's_carousel', 's_timeline', 's_quadrant'],
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_carousel'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'data_attributes': {
                'columns': '2',
                'alignment': 'right',
            },
            'add_classes': [
                'pt88', 'pb88',
                {
                    's_dynamic_snippet_title': 's_dynamic_snippet_title_aside col-lg-3 flex-lg-column justify-content-lg-start'
                },
            ],
            'remove_classes': [
                'pt64', 'pb64',
            ],
        },
    },
    'depends': ['theme_common'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.assets_editor': [
            'theme_avantgarde/static/src/js/tour.js',
        ],
    }
}
