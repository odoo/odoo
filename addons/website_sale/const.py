import re

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__, default_lang='en_US')

# Website configurator

SHOP_PAGE_STYLE_MAPPING = {
    'classic_grid': {
        'title': _lt("Classic Grid"),
        'img_src': '/website_sale/static/src/img/configurator/shop/classic_grid.jpg',
        'views': {
            'enable': [
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [],
        },
        'website_fields': {
            'shop_opt_products_design_classes': 'o_wsale_products_opt_layout_catalog '
                                                'o_wsale_products_opt_design_thumbs '
                                                'o_wsale_products_opt_name_color_regular '
                                                'o_wsale_products_opt_thumb_cover '
                                                'o_wsale_products_opt_img_secondary_show '
                                                'o_wsale_products_opt_img_hover_zoom_out_light '
                                                'o_wsale_products_opt_has_cta '
                                                'o_wsale_products_opt_actions_onhover '
                                                'o_wsale_products_opt_has_wishlist '
                                                'o_wsale_products_opt_wishlist_fixed '
                                                'o_wsale_products_opt_cc1 '
                                                'o_wsale_products_opt_rounded_2 '
                                                'o_wsale_products_opt_has_comparison '
                                                'o_wsale_products_opt_actions_promote',
        },
    },
    'modern_grid': {
        'title': _lt("Modern Grid"),
        'img_src': '/website_sale/static/src/img/configurator/shop/modern_grid.jpg',
        'views': {
            'enable': [
                'website.template_header_search',  # Header menu with search bar
                'website.header_width_full',  # Header width
                'website_sale.shop_fullwidth',  # Content Fullwidth
                'website_sale.products_mobile_cols_single',  # Mobile cols single
                'website_sale.filmstrip_categories_grid',  # Category style
                'website_sale.template_footer_website_sale',  # Footer
                'website.footer_copyright_content_width_fluid',  # Footer width
            ],
            'disable': [],
        },
        'website_fields': {
            'shop_ppr': 5,
            'shop_gap': '0px',
            'shop_opt_products_design_classes': 'o_wsale_products_opt_thumb_cover '
                                                'o_wsale_products_opt_img_hover_zoom_out_light '
                                                'o_wsale_products_opt_has_cta '
                                                'o_wsale_products_opt_has_wishlist '
                                                'o_wsale_products_opt_has_comparison '
                                                'o_wsale_products_opt_actions_onhover '
                                                'o_wsale_products_opt_wishlist_fixed '
                                                'o_wsale_products_opt_layout_catalog '
                                                'o_wsale_products_opt_design_grid '
                                                'o_wsale_products_opt_actions_theme '
                                                'o_wsale_products_opt_img_secondary_show '
                                                'o_wsale_products_opt_thumb_4_5 '
                                                'o_wsale_products_opt_text_align_center',
        },
        'scss_customization_params': {
            'header-links-style': 'default',
            'header-template': 'search',
        },
    },
    'showcase': {
        'title': _lt("Showcase"),
        'img_src': '/website_sale/static/src/img/configurator/shop/showcase.jpg',
        'views': {
            'enable': [
                'website.template_header_sales_four',  # Header
                'website.header_width_full',  # Header width
                'website_sale.shop_fullwidth',  # Content fullwidth
                'website_sale.filmstrip_categories_pills',  # Category style
                'website_sale.products_attributes_top',  # Filters
                'website_sale.floating_bar',  # Toolbar/floating
                'website_sale.template_footer_website_sale',  # Footer
                'website.footer_copyright_content_width_fluid',  # Footer width
            ],
            'disable': [
                'website_sale.products_attributes',  # Filters
            ],
        },
        'website_fields': {
            'shop_gap': '0px',
            'shop_opt_products_design_classes': 'o_wsale_products_opt_name_color_regular '
                                                'o_wsale_products_opt_thumb_cover '
                                                'o_wsale_products_opt_has_description '
                                                'o_wsale_products_opt_cc o_wsale_products_opt_cc5 '
                                                'o_wsale_products_opt_layout_list '
                                                'o_wsale_products_opt_design_showcase '
                                                'o_wsale_products_opt_thumb_4_5 '
                                                'o_wsale_products_opt_has_wishlist '
                                                'o_wsale_products_opt_actions_onhover '
                                                'o_wsale_products_opt_wishlist_fixed '
                                                'o_wsale_products_opt_actions_subtle',
        },
        'scss_customization_params': {
            'header-links-style': 'default',
            'header-template': 'sales_four',
        },
    },
    'chips_contained': {
        'title': _lt("Chips Contained"),
        'img_src': '/website_sale/static/src/img/configurator/shop/chips_contained.jpg',
        'views': {
            'enable': [
                'website.template_header_sales_one',  # Header
                'website_sale.products_mobile_cols_single',  # Mobile cols single
                'website_sale.filmstrip_categories_bordered',  # Category style
                'website_sale.products_attributes_top',  # Filters
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [
                'website_sale.products_attributes',  # Filters
            ],
        },
        'website_fields': {
            'shop_ppr': 4,
            'shop_gap': '16px',
            'shop_opt_products_design_classes': 'o_wsale_products_opt_name_color_regular '
                                                'o_wsale_products_opt_thumb_cover '
                                                'o_wsale_products_opt_img_secondary_show '
                                                'o_wsale_products_opt_img_hover_zoom_out_light '
                                                'o_wsale_products_opt_has_cta '
                                                'o_wsale_products_opt_has_wishlist '
                                                'o_wsale_products_opt_has_comparison '
                                                'o_wsale_products_opt_actions_inline '
                                                'o_wsale_products_opt_wishlist_inline '
                                                'o_wsale_products_opt_actions_promote '
                                                'o_wsale_products_opt_cc o_wsale_products_opt_cc1 '
                                                'o_wsale_products_opt_rounded_4 '
                                                'o_wsale_products_opt_layout_catalog '
                                                'o_wsale_products_opt_design_chips',
        },
        'scss_customization_params': {
            'header-links-style': 'default',
            'header-template': 'sales_one',
        },
    },
    'condensed_list': {
        'title': _lt("Condensed List"),
        'img_src': '/website_sale/static/src/img/configurator/shop/condensed_list.jpg',
        'views': {
            'enable': [
                'website.template_header_hamburger',  # Header
                'website.no_autohide_menu',  # Header
                'website_sale.filmstrip_categories_images',  # Category style
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [],
        },
        'website_fields': {
            'shop_gap': '16px',
            'shop_opt_products_design_classes': 'o_wsale_products_opt_name_color_regular '
                                                'o_wsale_products_opt_thumb_cover '
                                                'o_wsale_products_opt_has_cta '
                                                'o_wsale_products_opt_has_wishlist '
                                                'o_wsale_products_opt_actions_inline '
                                                'o_wsale_products_opt_cc o_wsale_products_opt_cc1 '
                                                'o_wsale_products_opt_rounded_2 '
                                                'o_wsale_products_opt_img_secondary_show '
                                                'o_wsale_products_opt_actions_promote '
                                                'o_wsale_products_opt_layout_list '
                                                'o_wsale_products_opt_design_thumbs',
        },
        'scss_customization_params': {
            'header-links-style': 'default',
            'header-template': 'hamburger',
        },
    },
    'cards': {
        'title': _lt("Cards"),
        'img_src': '/website_sale/static/src/img/configurator/shop/cards.jpg',
        'views': {
            'enable': [
                'website_sale.products_mobile_cols_single',  # Mobile cols single
                'website_sale.filmstrip_categories_large_images',  # Category style
                'website_sale.products_attributes_top',  # Filters
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [
                'website_sale.products_attributes',  # Filters
            ],
        },
        'website_fields': {
            'shop_ppr': 4,
            'shop_gap': '8px',
            'shop_opt_products_design_classes': 'o_wsale_products_opt_name_color_regular '
                                                'o_wsale_products_opt_thumb_cover '
                                                'o_wsale_products_opt_img_secondary_show '
                                                'o_wsale_products_opt_img_hover_zoom_out_light '
                                                'o_wsale_products_opt_has_cta '
                                                'o_wsale_products_opt_has_wishlist '
                                                'o_wsale_products_opt_actions_onhover '
                                                'o_wsale_products_opt_wishlist_fixed '
                                                'o_wsale_products_opt_actions_subtle '
                                                'o_wsale_products_opt_rounded_2 '
                                                'o_wsale_products_opt_layout_catalog '
                                                'o_wsale_products_opt_design_cards '
                                                'o_wsale_products_opt_thumb_4_5 '
                                                'o_wsale_products_opt_has_comparison',
        },
    },
}

PRODUCT_PAGE_STYLE_MAPPING = {
    'classic': {
        'title': _lt("Classic"),
        'img_src': '/website_sale/static/src/img/configurator/product/classic.jpg',
        'views': {
            'enable': [
                'website_sale.carousel_product_indicators_left',  # Layout/Thumbnails
            ],
            'disable': [
                'website_sale.carousel_product_indicators_bottom',  # Layout/Thumbnails
                'website_sale_comparison.product_add_to_compare',  # Comparison
                'website_sale.product_terms_and_conditions',  # Terms and Conditions
            ],
        },
        'website_fields': {},  # Default
    },
    'image_grid': {
        'title': _lt("Image Grid"),
        'img_src': '/website_sale/static/src/img/configurator/product/image_grid.jpg',
        'views': {
            'enable': [
                'website_sale.product_picture_magnify_click',
            ],
            'disable': [
                'website_sale.product_picture_magnify_hover',
                'website_sale.product_picture_magnify_both',
                'website_sale_comparison.product_add_to_compare',  # Comparison
                'website_sale.product_terms_and_conditions',  # Terms and Conditions
            ],
        },
        'website_fields': {
            'product_page_image_layout': 'grid',
            'product_page_image_width': '66_pc',
        },
    },
    'focused': {
        'title': _lt("Focused"),
        'img_src': '/website_sale/static/src/img/configurator/product/focused.jpg',
        'views': {
            'enable': [
                'website_sale.products_carousel_4x3',
            ],
            'disable': [
                'website_sale.products_carousel_4x5',
                'website_sale.products_carousel_16x9',
                'website_sale.products_carousel_21x9',
                'website_sale_comparison.product_add_to_compare',  # Comparison
                'website_sale.product_terms_and_conditions',  # Terms and Conditions
            ],
        },
        'website_fields': {
            'product_page_image_width': '66_pc',
        },
    },
    'large_image': {
        'title': _lt("Large Image"),
        'img_src': '/website_sale/static/src/img/configurator/product/large_image.jpg',
        'views': {
            'enable': [
                'website_sale.product_picture_magnify_click',
            ],
            'disable': [
                'website_sale.product_picture_magnify_hover',
                'website_sale.product_picture_magnify_both',
                'website_sale_comparison.product_add_to_compare',  # Comparison
                'website_sale.product_terms_and_conditions',  # Terms and Conditions
            ],
        },
        'website_fields': {
            'product_page_image_width': '100_pc',
        },
    },
}

# Google Merchant Center

GMC_SUPPORTED_UOM = {
    'oz',
    'lb',
    'mg',
    'g',
    'kg',
    'floz',
    'pt',
    'qt',
    'gal',
    'ml',
    'cl',
    'l',
    'cbm',
    'in',
    'ft',
    'yd',
    'cm',
    'm',
    'sqft',
    'sqm',
}

GMC_BASE_MEASURE = re.compile(r'(?P<base_count>\d+)?\s*(?P<base_unit>[a-z]+)')

SHOP_PATH = '/shop'
