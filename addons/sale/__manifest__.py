# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Sales',
    'version': '1.2',
    'category': 'Sales/Sales',
    'summary': 'Sales internal machinery',
    'description': """
This module contains all the common features of Sales Management and eCommerce.
    """,
    'depends': [
        'sales_team',
        'account_payment',  # -> account, payment, portal
        'utm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'security/ir_rules.xml',

        'report/account_invoice_report_views.xml',
        'report/ir_actions_report_templates.xml',
        'report/ir_actions_report.xml',
        'report/sale_report_views.xml',

        'data/ir_cron.xml',
        'data/ir_sequence_data.xml',
        'data/mail_activity_type_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_template_data.xml',
        'data/sale_tour.xml',
        'data/ir_config_parameter.xml', # Needs mail_template_data

        'wizard/account_accrued_orders_wizard_views.xml',
        'wizard/mass_cancel_orders_views.xml',
        'wizard/payment_link_wizard_views.xml',
        'wizard/res_config_settings_views.xml',
        'wizard/sale_make_invoice_advance_views.xml',
        'wizard/sale_order_cancel_views.xml',
        'wizard/sale_order_discount_views.xml',

        # Define sale order views before their references
        'views/sale_order_views.xml',

        'views/account_views.xml',
        'views/crm_team_views.xml',
        'views/mail_activity_views.xml',
        'views/mail_activity_plan_views.xml',
        'views/payment_views.xml',
        'views/product_document_views.xml',
        'views/product_packaging_views.xml',
        'views/product_template_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_line_views.xml',
        'views/sale_portal_templates.xml',
        'views/utm_campaign_views.xml',

        'views/sale_menus.xml',  # Last because referencing actions defined in previous files
    ],
    'demo': [
        'data/product_demo.xml',
        'data/sale_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'sale/static/src/scss/sale_onboarding.scss',
            'sale/static/src/js/badge_extra_price/*',
            'sale/static/src/js/sale_action_helper/*',
            'sale/static/src/js/combo_configurator_dialog/*',
            'sale/static/src/js/models/*',
            'sale/static/src/js/product/*',
            'sale/static/src/js/product_card/*',
            'sale/static/src/js/product_configurator_dialog/*',
            'sale/static/src/js/product_list/*',
            'sale/static/src/js/product_template_attribute_line/*',
            'sale/static/src/js/quantity_buttons/*',
            'sale/static/src/js/sale_order_line_field/*',
            'sale/static/src/js/sale_progressbar_field.js',
            'sale/static/src/js/tours/sale.js',
            'sale/static/src/js/sale_product_field.js',
            'sale/static/src/js/sale_product_field.scss',
            'sale/static/src/js/sale_utils.js',
            'sale/static/src/xml/**/*',
            'sale/static/src/views/**/*',
        ],
        'web.assets_frontend': [
            'sale/static/src/scss/sale_portal.scss',
            'sale/static/src/js/sale_portal_sidebar.js',
            'sale/static/src/js/sale_portal_prepayment.js',
            'sale/static/src/js/sale_portal.js',
        ],
        'web.assets_tests': [
            'sale/static/tests/tours/**/*',
            'sale/static/src/js/tours/product_configurator_tour_utils.js',
            'sale/static/src/js/tours/tour_utils.js',
        ],
        'web.assets_unit_tests': [
            'sale/static/tests/mock_server/**/*',
        ],
        'web.qunit_suite_tests': [
            'sale/static/tests/**/*',
            ('remove', 'sale/static/tests/tours/**/*'),
            ('remove', 'sale/static/tests/mock_server/**/*'),
        ],
        'web.report_assets_common': [
            'sale/static/src/scss/sale_report.scss',
        ],
    },
    'post_init_hook': '_post_init_hook',
    'license': 'LGPL-3',
}
