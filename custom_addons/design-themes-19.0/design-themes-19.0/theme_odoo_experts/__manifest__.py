{
    'name': 'Experts Theme',
    'description': 'Experts Business Theme',
    'category': 'Theme/Corporate',
    'summary': 'Advisor, Corporate, Service, Business, Finance, IT',
    'sequence': 210,
    'version': '2.1.0',
    'depends': ['theme_common'],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'views/images.xml',

        'views/snippets/s_carousel_intro.xml',
        'views/snippets/s_cta_box.xml',
        'views/snippets/s_banner.xml',
        'views/snippets/s_striped_top.xml',
        'views/snippets/s_media_list.xml',
        'views/snippets/s_image_text.xml',
        'views/snippets/s_call_to_action.xml',
        'views/snippets/s_text_image.xml',
        'views/snippets/s_company_team.xml',
        'views/snippets/s_references.xml',
        'views/snippets/s_references_social.xml',
        'views/snippets/s_references_grid.xml',
        'views/snippets/s_freegrid.xml',
        'views/snippets/s_cover.xml',
        'views/snippets/s_card_offset.xml',
        'views/snippets/s_numbers.xml',
        'views/snippets/s_three_columns.xml',
        'views/snippets/s_color_blocks_2.xml',
        'views/snippets/s_image_gallery.xml',
        'views/snippets/s_comparisons.xml',
        'views/snippets/s_product_catalog.xml',
        'views/snippets/s_features_grid.xml',
        'views/snippets/s_product_list.xml',
        'views/snippets/s_quotes_carousel.xml',
        'views/snippets/s_quotes_carousel_minimal.xml',
        'views/snippets/s_picture.xml',
        'views/snippets/s_title.xml',
        'views/snippets/s_unveil.xml',
        'views/snippets/s_key_benefits.xml',
        'views/snippets/s_carousel.xml',
        'views/snippets/s_pricelist_boxed.xml',
        'views/snippets/s_striped_center_top.xml',
        'views/snippets/s_image_title.xml',
        'views/snippets/s_key_images.xml',
        'views/snippets/s_quadrant.xml',
        'views/snippets/s_big_number.xml',
        'views/snippets/s_wavy_grid.xml',
        'views/snippets/s_empowerment.xml',
        'views/snippets/s_numbers_list.xml',
        'views/snippets/s_showcase.xml',
        'views/snippets/s_mockup_image.xml',
        'views/snippets/s_numbers_boxed.xml',
        'views/snippets/s_company_team_card.xml',
        'views/snippets/s_numbers_framed.xml',
        'views/new_page_template.xml',
    ],
    'images': [
        'static/description/odoo_experts_description.webp',
        'static/description/odoo_experts_screenshot.webp',
    ],
    'images_preview_theme': {
        'website.s_mockup_image_default_image': '/theme_odoo_experts/static/src/img/snippets/s_mockup_image_default_image.jpg',
        'website.s_text_image_default_image': '/theme_odoo_experts/static/src/img/snippets/s_text_image.webp',
        'website.s_image_text_default_image': '/theme_odoo_experts/static/src/img/snippets/s_image_text.webp',
        'website.s_showcase_default_image': '/theme_odoo_experts/static/src/img/snippets/s_showcase_default_image.webp',
        'website.library_image_08': '/theme_odoo_experts/static/src/img/snippets/library_image_08.webp',
        'website.s_picture_default_image': '/theme_odoo_experts/static/src/img/snippets/s_picture.webp',
    },
    'configurator_snippets': {
        'homepage': ['s_mockup_image', 's_references', 's_image_text', 's_text_image', 's_showcase', 's_faq_collapse', 's_cta_box'],
    },
    'configurator_snippets_addons': {
        'website_sale': {
            'homepage': [
                ('website_sale.s_dynamic_snippet_category_list', 'after', 's_showcase'),
            ],
        },
    },
    'theme_customizations': {
        'website_sale.s_dynamic_snippet_category_list': {
            'template_key': (
                'website_sale.dynamic_filter_template_product_public_category_default'
            ),
            'data_attributes': {
                'rounded': '4',
                'gap': '4',
                'button': 'Explore Now'
            },
            'add_classes': [
                'pt40',
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
            'theme_odoo_experts/static/src/js/tour.js',
        ],
    }
}
