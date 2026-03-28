{
    'name': 'Graphene Theme',
    'description': 'Light colours, thin text, clean and sharp design.',
    'category': 'Theme/Corporate',
    'summary': 'Service, Corporate, Design, Technology, Robotics, Computers, IT, Blogs',
    'sequence': 110,
    'version': '2.0.0',
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/images_library.xml',
        'views/customizations.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/graphene_poster.webp',
        'static/description/graphene_screenshot.webp',
    ],
    'images_preview_theme': {
        'website.s_cover_default_image': '/theme_graphene/static/src/img/pictures/bg_image_08.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_cover', 's_text_image', 's_numbers_grid', 's_mockup_image', 's_comparisons', 's_references'],
    },
    'new_page_templates': {
        'about': {
            'personal': ['s_text_cover', 's_image_text', 's_text_block_h2', 's_numbers', 's_features', 's_call_to_action'],
        },
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_mockup_image'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'data_attributes': {
                'alignment': 'left',
            },
            'template_key': (
                'website_sale.dynamic_filter_template_product_public_category_default'
            ),
            'background': {
                'color': 'o_cc2',
            },
            'add_classes': [
                'pt96', 'pb96',
                {
                    's_dynamic_snippet_title': 'd-none',
                },
            ],
            'remove_classes': [
                's_dynamic_category_clickable_items', 'pt64', 'pb64',
            ],
        },
    },
    'depends': ['theme_common'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.assets_editor': [
            'theme_graphene/static/src/js/tour.js',
        ],
    }
}
