{
    'name': 'Vehicle Theme',
    'description': 'Vehicle Theme - Cars, Motorbikes, Bikes, Tires',
    'category': 'Theme/Services',
    'summary': 'Vehicle, Cars, Motorbikes, Bikes, Tires, Transports, Repair, Mechanics, Garages, Sports, Services',
    'sequence': 300,
    'version': '2.0.0',
    'depends': ['theme_common'],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/images.xml',
        'views/customizations.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/vehicle_description.png',
        'static/description/vehicle_screenshot.png',
    ],
    'images_preview_theme': {
        'website.s_cover_default_image': '/theme_vehicle/static/src/img/snippets/s_cover.webp',
        'website.s_three_columns_default_image_1': '/theme_vehicle/static/src/img/snippets/s_three_columns_1.webp',
        'website.s_three_columns_default_image_2': '/theme_vehicle/static/src/img/snippets/s_three_columns_2.webp',
        'website.s_three_columns_default_image_3': '/theme_vehicle/static/src/img/snippets/s_three_columns_3.webp',
        'website.s_picture_default_image': '/theme_vehicle/static/src/img/snippets/s_picture.webp',
        'website.s_key_images_default_image_1': '/theme_vehicle/static/src/img/snippets/s_images_wall_5.webp',
        'website.s_key_images_default_image_2': '/theme_vehicle/static/src/img/snippets/s_img_gallery_1.webp',
        'website.s_key_images_default_image_3': '/theme_vehicle/static/src/img/snippets/s_masonry_block_2.webp',
        'website.s_key_images_default_image_4': '/theme_vehicle/static/src/img/snippets/s_images_wall_2.webp',
        'website.s_media_list_default_image_1': '/theme_vehicle/static/src/img/snippets/s_media_list_1.webp',
        'website.s_media_list_default_image_2': '/theme_vehicle/static/src/img/snippets/s_media_list_2.webp',
        'website.s_media_list_default_image_3': '/theme_vehicle/static/src/img/snippets/s_media_list_3.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_cover', 's_title', 's_three_columns', 's_picture', 's_key_images', 's_numbers_charts', 's_media_list'],
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_picture'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'template_key': (
                'website_sale.dynamic_filter_template_product_public_category_default'
            ),
            'data_attributes': {
                'gap': '4',
                'alignment': 'left',
            },
            'background': {
                'color': 'o_cc2',
            },
            'add_classes': [
                'pt80', 'pb88',
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
        'team': {
            '5': ['s_text_block_h1', 's_text_block', 's_image_gallery', 's_picture'],
        },
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.assets_editor': [
            'theme_vehicle/static/src/js/tour.js',
        ],
    }
}
