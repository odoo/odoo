{
    'name': 'Be Wise Theme',
    'description': 'Be Wise Theme',
    'category': 'Theme/Education',
    'summary': 'University, Education, Schools, Young, Play, Kids',
    'sequence': 240,
    'version': '3.0.0',
    'depends': ['theme_common'],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/image_content.xml',
        'views/customizations.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/bewise_description.webp',
        'static/description/bewise_screenshot.webp',
    ],
    'images_preview_theme': {
        'website.s_picture_default_image': '/theme_bewise/static/src/img/content/college_library.webp',
        'website.s_media_list_default_image_1': '/theme_bewise/static/src/img/content/college_media_1.webp',
        'website.s_media_list_default_image_2': '/theme_bewise/static/src/img/content/college_media_2.webp',
        'website.s_masonry_block_default_image_1': '/theme_bewise/static/src/img/content/content_img_25.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_striped_center_top', 's_title', 's_color_blocks_2', 's_faq_collapse', 's_masonry_block_default_template', 's_company_team_shapes'],
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_striped_center_top'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'data_attributes': {
                'rounded': '3',
                'size': 'small',
            },
            'add_classes': [
                'pb128',
                {
                    's_dynamic_snippet_title': 'd-none'
                },
            ],
            'remove_classes': [
                'pt64', 'pb64',
            ],
        },
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.assets_editor': [
            'theme_bewise/static/src/js/tour.js',
        ],
    }
}
