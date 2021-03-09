# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'eCommerce',
    'category': 'Website/Website',
    'sequence': 50,
    'summary': 'Sell your products online',
    'website': 'https://www.odoo.com/page/e-commerce',
    'version': '1.1',
    'description': "",
    'depends': ['website', 'sale', 'website_payment', 'website_mail', 'website_form', 'portal_rating', 'digest'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_sale.xml',
        'data/data.xml',
        'data/mail_template_data.xml',
        'data/digest_data.xml',
        'views/product_views.xml',
        'views/account_views.xml',
        'views/onboarding_views.xml',
        'views/sale_report_views.xml',
        'views/sale_order_views.xml',
        'views/crm_team_views.xml',
        'views/templates.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_dynamic_snippet_products.xml',
        'views/snippets/s_products_searchbar.xml',
        'views/res_config_settings_views.xml',
        'views/digest_views.xml',
        'views/website_sale_visitor_views.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
    'application': True,
    'pre_init_hook': 'pre_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            # after //script[last()]
            'website_sale/static/src/snippets/s_dynamic_snippet_products/000.js',
            # after //script[last()]
            'website_sale/static/src/snippets/s_products_searchbar/000.js',
            # after link[last()]
            'website_sale/static/src/scss/website_sale.scss',
            # after link[last()]
            'website_sale/static/src/scss/website_mail.scss',
            # after link[last()]
            'website_sale/static/src/scss/website_sale_frontend.scss',
            # after link[last()]
            'sale/static/src/scss/sale_portal.scss',
            # after link[last()]
            'sale/static/src/scss/product_configurator.scss',
            # after script[last()]
            'sale/static/src/js/variant_mixin.js',
            # after script[last()]
            'website_sale/static/src/js/variant_mixin.js',
            # after script[last()]
            'website_sale/static/src/js/website_sale.js',
            # after script[last()]
            'website_sale/static/src/js/website_sale_utils.js',
            # after script[last()]
            'website_sale/static/src/js/website_sale_payment.js',
            # after script[last()]
            'website_sale/static/src/js/website_sale_validate.js',
            # after script[last()]
            'website_sale/static/src/js/website_sale_recently_viewed.js',
            # after script[last()]
            'website_sale/static/src/js/website_sale_tracking.js',
        ],
        'web._assets_primary_variables': [
            # after //link[last()]
            'website_sale/static/src/scss/primary_variables.scss',
        ],
        'web.assets_backend': [
            # inside .
            'website_sale/static/src/js/website_sale_video_field_preview.js',
            # inside .
            'website_sale/static/src/js/website_sale_backend.js',
            # inside .
            'website_sale/static/src/scss/website_sale_dashboard.scss',
            # inside .
            'website_sale/static/src/scss/website_sale_backend.scss',
            # inside .
            'website_sale/static/src/js/tours/website_sale_shop_backend.js',
        ],
        'website.assets_wysiwyg': [
            # after //link[last()]
            'website_sale/static/src/scss/website_sale.editor.scss',
            # after //link[last()]
            'website_sale/static/src/snippets/s_dynamic_snippet_products/options.js',
        ],
        'website.assets_editor': [
            # after //script[last()]
            'website_sale/static/src/js/website_sale.editor.js',
            # after //script[last()]
            'website_sale/static/src/js/website_sale_form_editor.js',
            # after //script[last()]
            'website_sale/static/src/js/tours/website_sale_shop_frontend.js',
        ],
        'web.assets_common': [
            # inside .
            'website_sale/static/src/js/tours/website_sale_shop.js',
        ],
        'web.assets_tests': [
            # inside .
            'website_sale/static/tests/tours/website_sale_buy.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_complete_flow.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_cart_recovery.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_mail.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_customize.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_custom_attribute_value.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_zoom.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_dynamic_variants.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_deleted_archived_variants.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_list_view_b2c.js',
            # inside .
            'website_sale/static/tests/tours/website_sale_shop_no_variant_attribute.js',
        ],
        'web.assets_qweb': [
            'website_sale/static/src/xml/*.xml',
        ],
    }
}
