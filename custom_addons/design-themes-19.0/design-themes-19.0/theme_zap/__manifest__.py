{
    'name': 'Zap Theme',
    'description': 'Zap Theme - Corporate, Business, Marketing, Copywriting',
    'category': 'Theme/Corporate',
    'summary': 'Digital, Marketing, Copywriting, Media, Events, Non Profit, NGO, Corporate, Business, Services',
    'sequence': 160,
    'version': '2.0.0',
    'depends': ['theme_common'],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/images_library.xml',

        'views/snippets/s_cta_box.xml',
        'views/snippets/s_banner.xml',
        'views/snippets/s_discovery.xml',
        'views/snippets/s_comparisons.xml',
        'views/snippets/s_comparisons_horizontal.xml',
        'views/snippets/s_showcase.xml',
        'views/snippets/s_cta_card.xml',
        'views/snippets/s_striped_top.xml',
        'views/snippets/s_call_to_action.xml',
        'views/snippets/s_sidegrid.xml',
        'views/snippets/s_carousel_intro.xml',
        'views/snippets/s_color_blocks_2.xml',
        'views/snippets/s_company_team_basic.xml',
        'views/snippets/s_cover.xml',
        'views/snippets/s_card_offset.xml',
        'views/snippets/s_features.xml',
        'views/snippets/s_masonry_block.xml',
        'views/snippets/s_media_list.xml',
        'views/snippets/s_numbers.xml',
        'views/snippets/s_numbers_charts.xml',
        'views/snippets/s_references.xml',
        'views/snippets/s_references_social.xml',
        'views/snippets/s_references_grid.xml',
        'views/snippets/s_image_text.xml',
        'views/snippets/s_key_images.xml',
        'views/snippets/s_three_columns.xml',
        'views/snippets/s_image_gallery.xml',
        'views/snippets/s_freegrid.xml',
        'views/snippets/s_quadrant.xml',
        'views/snippets/s_framed_intro.xml',
        'views/snippets/s_unveil.xml',
        'views/snippets/s_numbers_showcase.xml',
        'views/snippets/s_key_benefits.xml',
        'views/snippets/s_pricelist_boxed.xml',
        'views/snippets/s_striped_center_top.xml',
        'views/snippets/s_striped.xml',
        'views/snippets/s_company_team_card.xml',
        'views/snippets/s_image_title.xml',
        'views/snippets/s_big_number.xml',
        'views/snippets/s_images_constellation.xml',
        'views/snippets/s_empowerment.xml',
        'views/snippets/s_numbers_framed.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/zap_cover.gif',
        'static/description/zap_screenshot.webp',
    ],
    'images_preview_theme': {
        'website.s_image_text_default_image': '/theme_zap/static/src/img/content/s_image_text.webp',
        'website.s_media_list_default_image_1': '/theme_zap/static/src/img/content/media_list_01.webp',
        'website.s_media_list_default_image_2': '/theme_zap/static/src/img/content/media_list_02.webp',
        'website.s_text_cover_default_image': '/theme_zap/static/src/img/snippets/s_cover.webp',
        'website.s_text_image_default_image': '/theme_zap/static/src/img/content/s_text_image.webp',
        'website.s_three_columns_default_image_3': '/theme_zap/static/src/img/content/three_columns_03.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_discovery', 's_key_images', 's_striped', 's_showcase', 's_image_title', 's_numbers_charts', 's_cta_card'],
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_striped'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'template_key': (
                'website_sale.dynamic_filter_template_product_public_category_default'
            ),
            'data_attributes': {
                'rounded': '0',
                'gap': '4',
                'alignment': 'left',
            },
            'add_classes': [
                'pt0',
                {
                    's_dynamic_snippet_title': 'd-none'
                },
            ],
            'remove_classes': [
                's_dynamic_category_clickable_items', 'pt64',
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
            'theme_zap/static/src/js/tour.js',
        ],
    }
}
