{
    'name': 'Enark Theme',
    'description': 'Enark Theme',
    'category': 'Theme/Corporate',
    'summary': 'Architect, Corporate, Business, Finance, Services',
    'sequence': 190,
    'version': '2.0.0',
    'depends': ['theme_common'],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/image_library.xml',

        'views/snippets/s_closer_look.xml',
        'views/snippets/s_cta_box.xml',
        'views/snippets/s_banner.xml',
        'views/snippets/s_striped_top.xml',
        'views/snippets/s_cards_grid.xml',
        'views/snippets/s_comparisons_horizontal.xml',
        'views/snippets/s_cover.xml',
        'views/snippets/s_card_offset.xml',
        'views/snippets/s_company_team_detail.xml',
        'views/snippets/s_text_image.xml',
        'views/snippets/s_title.xml',
        'views/snippets/s_picture.xml',
        'views/snippets/s_quotes_carousel_minimal.xml',
        'views/snippets/s_quotes_carousel_compact.xml',
        'views/snippets/s_pricelist_boxed.xml',
        'views/snippets/s_freegrid.xml',
        'views/snippets/s_sidegrid.xml',
        'views/snippets/s_media_list.xml',
        'views/snippets/s_numbers_list.xml',
        'views/snippets/s_call_to_action.xml',
        'views/snippets/s_parallax.xml',
        'views/snippets/s_image_gallery.xml',
        'views/snippets/s_features_wall.xml',
        'views/snippets/s_image_title.xml',
        'views/snippets/s_key_images.xml',
        'views/snippets/s_quadrant.xml',
        'views/snippets/s_images_mosaic.xml',
        'views/snippets/s_references.xml',
        'views/snippets/s_unveil.xml',
        'views/snippets/s_key_benefits.xml',
        'views/snippets/s_carousel.xml',
        'views/snippets/s_carousel_intro.xml',
        'views/snippets/s_striped_center_top.xml',
        'views/snippets/s_intro_pill.xml',
        'views/snippets/s_big_number.xml',
        'views/snippets/s_image_frame.xml',
        'views/snippets/s_wavy_grid.xml',
        'views/snippets/s_shape_image.xml',
        'views/snippets/s_images_constellation.xml',
        'views/snippets/s_text_cover.xml',
        'views/snippets/s_empowerment.xml',
        'views/snippets/s_split_intro.xml',
        'views/snippets/s_numbers_framed.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/enark_description.webp',
        'static/description/enark_screenshot.webp',
    ],
    'images_preview_theme': {
        'website.library_image_03': '/theme_enark/static/src/img/snippets/library_image_03.webp',
        'website.library_image_13': '/theme_enark/static/src/img/snippets/library_image_13.webp',
        'website.library_image_10': '/theme_enark/static/src/img/snippets/library_image_10.webp',
        'website.library_image_05': '/theme_enark/static/src/img/snippets/library_image_05.webp',
        'website.library_image_14': '/theme_enark/static/src/img/snippets/library_image_14.webp',
        'website.library_image_16': '/theme_enark/static/src/img/snippets/library_image_16.webp',
        'website.library_image_02': '/theme_enark/static/src/img/snippets/library_image_02.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_freegrid', 's_features_wall', 's_numbers_list', 's_title', 's_images_wall', 's_references', 's_cta_box'],
    },
    'new_page_templates': {
        'about': {
            'personal': ['s_text_cover', 's_image_text', 's_text_block_h2', 's_numbers', 's_features', 's_call_to_action'],
        },
        'landing': {
            '1': ['s_banner', 's_features', 's_masonry_block_default_template', 's_call_to_action', 's_references', 's_quotes_carousel'],
            '2': ['s_cover', 's_text_image', 's_text_block_h2', 's_three_columns_landing_1', 's_call_to_action'],
            '3': ['s_text_cover', 's_text_block_h2', 's_three_columns', 's_showcase', 's_color_blocks_2', 's_quotes_carousel', 's_call_to_action'],
        },
        'services': {
            '2': ['s_text_cover', 's_image_text', 's_text_image', 's_image_text_2nd', 's_call_to_action'],
        },
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_freegrid'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'data_attributes': {
                'gap': '3',
                'rounded': '0',
                'size': 'small',
            },
            'background': {
                'shape': {
                    'data-oe-shape-data': '{"shape":"web_editor/Connections/20","flip":["y"],"colors":{"c5":"o-color-5"}}',
                    'element': """<div class="o_we_shape o_web_editor_Connections_20" style="background-image: url('/web_editor/shape/web_editor/Connections/20.svg?c5=o-color-5'); background-position: 50% 0%;""",
                },
            },
            'add_classes': [
                'pb48', 'pt88',
                {
                    's_dynamic_snippet_title': 'd-none',
                },
            ],
            'remove_classes': [
                'pb64', 'pt64',
            ],
        },
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.assets_editor': [
            'theme_enark/static/src/js/tour.js',
        ],
    }
}
