{
    'name': 'Monglia Theme',
    'description': 'Monglia Catering Theme',
    'category': 'Theme/Services',
    'summary': 'Event, Restaurants, Bars, Pubs, Cafes, Catering, Food, Drinks, Concerts, Shows, Musics, Dance, Party',
    'sequence': 260,
    'version': '2.0.0',
    'depends': ['theme_common'],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/images_content.xml',
        'views/customizations.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/monglia_description.png',
        'static/description/monglia_screenshot.webp',
    ],
    'images_preview_theme': {
        'website.s_cover_default_image': '/theme_monglia/static/src/img/snippets/s_cover.webp',
        'website.s_media_list_default_image_1': '/theme_monglia/static/src/img/snippets/s_media_list_1.webp',
        'website.s_media_list_default_image_2': '/theme_monglia/static/src/img/snippets/s_media_list_2.webp',
        'website.s_media_list_default_image_3': '/theme_monglia/static/src/img/snippets/s_media_list_3.webp',
        'website.s_text_image_default_image': '/theme_monglia/static/src/img/snippets/s_text_image.webp',
        'website.s_three_columns_default_image_1': '/theme_monglia/static/src/img/snippets/library_image_11.webp',
        'website.s_three_columns_default_image_2': '/theme_monglia/static/src/img/snippets/library_image_13.webp',
        'website.s_three_columns_default_image_3': '/theme_monglia/static/src/img/snippets/library_image_07.webp',
        'website.library_image_03': '/theme_monglia/static/src/img/snippets/library_image_03.webp',
        'website.library_image_10': '/theme_monglia/static/src/img/snippets/library_image_10.webp',
        'website.library_image_13': '/theme_monglia/static/src/img/snippets/library_image_23.webp',
        'website.library_image_02': '/theme_monglia/static/src/img/snippets/library_image_05.webp',
        'website.library_image_14': '/theme_monglia/static/src/img/snippets/library_image_14.webp',
        'website.library_image_16': '/theme_monglia/static/src/img/snippets/library_image_16.webp',
        'website.s_masonry_block_default_image_1': '/theme_monglia/static/src/img/snippets/s_masonry_block.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_cover', 's_numbers_grid', 's_company_team_shapes', 's_text_block', 's_freegrid', 's_cta_box', 's_shape_image', 's_title', 's_images_wall', 's_faq_collapse', 's_references'],
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_shape_image'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'data_attributes': {
                'columns': '2',
                'rounded': '4',
                'gap': '4',
            },
            'background': {
                'color': 'o_cc4',
            },
            'add_classes': [
                'pb88',
                {
                    's_dynamic_snippet_title': 'd-none'
                },
            ],
            'remove_classes': [
                'pt64', 'pb64',
            ],
        },
    },
    'new_page_templates': {
        'about': {
            'personal': ['s_text_cover', 's_image_text', 's_text_block_h2', 's_numbers', 's_features', 's_call_to_action'],
        },
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.assets_editor': [
            'theme_monglia/static/src/js/tour.js',
        ],
    }
}
