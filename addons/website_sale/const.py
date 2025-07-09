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
                'website.template_header_sales_one',  # Header
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [],
        },
        'website_fields': {},  # Default
    },
    'modern_showcase': {
        'title': _lt("Modern Showcase"),
        'img_src': '/website_sale/static/src/img/configurator/shop/modern_showcase.jpg',
        'views': {
            'enable': [
                'website_sale.shop_fullwidth',  # Content width
                'website_sale.products_design_grid',  # Style
                'website_sale.products_thumb_4_5',  # Style/Images size
                'website_sale.products_attributes_top',  # Filters
                'website_sale.floating_bar',  # Toolbar/floating
                'website.template_header_search',  # Header
                'website.header_width_full',  # Header width
                'website.footer_copyright_content_width_fluid',  # Copyright Footer width
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [
                'website_sale.products_design_card',  # Style
                'website_sale.products_design_thumbs',  # Style
                'website_sale.products_thumb_4_3',  # Images size
                'website_sale.products_thumb_2_3',  # Images size
                'website_sale.products_attributes',  # Filters
                'website.header_width_small',  # Header width
                'website.footer_copyright_content_width_small',  # Copyright Footer width
            ],
        },
        'website_fields': {
            'shop_ppr': 5,
            'shop_gap': '0px',
        },
    },
    'compact_list': {
        'title': _lt("Compact List"),
        'img_src': '/website_sale/static/src/img/configurator/shop/compact_list.jpg',
        'views': {
            'enable': [
                'website_sale.products_list_view',  # Listview layout
                'website_sale.products_description',  # Description
                'website.template_header_sales_two',  # Header
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [],
        },
        'website_fields': {},
    },
    'quick_browse_grid': {
        'title': _lt("Quick Browse Grid"),
        'img_src': '/website_sale/static/src/img/configurator/shop/quick_browse_grid.jpg',
        'views': {
            'enable': [
                'website_sale.products_design_card',  # Style
                'website_sale.products_categories',  # Categories sidebar
                'website_sale.option_collapse_products_categories',  # Categories/Collapse
                'website_sale.products_attributes_top',  # Filters
                'website.template_header_sales_four',  # Header
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [
                'website_sale.products_design_thumbs',  # Style
                'website_sale.products_design_grid',  # Style
                'website_sale.products_categories_top',  # Categories top
                'website_sale.products_attributes',  # Filters
            ],
        },
        'website_fields': {
            'shop_ppr': 5,
        },
    },
    'default_list': {
        'title': _lt("Detailed List"),
        'img_src': '/website_sale/static/src/img/configurator/shop/default_list.jpg',
        'views': {
            'enable': [
                'website_sale.products_list_view',  # Listview layout
                'website_sale.products_description',  # Description
                'website_sale.products_categories',  # Categories sidebar
                'website_sale.products_attributes_top',  # Filters
                'website_sale.floating_bar',  # Toolbar/floating
                'website.template_header_sales_three',  # Header
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [
                'website_sale.products_categories_top',  # Categories top
                'website_sale.products_attributes',  # Filters
            ],
        },
        'website_fields': {
            'shop_ppr': 4,
            'shop_gap': '28px',
        },
    },
    'sidebar_grid': {
        'title': _lt("Sidebar Grid"),
        'img_src': '/website_sale/static/src/img/configurator/shop/sidebar_grid.jpg',
        'views': {
            'enable': [
                'website_sale.products_design_grid',  # Style
                'website_sale.products_thumb_4_3',  # Style/Images sizes (Landscape)
                'website_sale.products_categories',  # Categories/Sidebar
                'website_sale.products_attributes_top',  # Filters
                'website.template_header_stretch',  # Header
                'website_sale.template_footer_website_sale',  # Footer
            ],
            'disable': [
                'website_sale.products_design_card',  # Style
                'website_sale.products_design_thumbs',  # Style
                'website_sale.products_thumb_4_5',  # Style/Images sizes
                'website_sale.products_thumb_2_3',  # Style/Images sizes
                'website_sale.products_categories_top',  # Categories/Top
                'website_sale.products_attributes',  # Filters
            ],
        },
        'website_fields': {
            'shop_ppr': 3,
            'shop_gap': '0px',
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
