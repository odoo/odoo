# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Delivery Costs',
    'version': '1.0',
    'category': 'Sales/Delivery',
    'description': """
Allows you to add delivery methods in sale orders.
==================================================
You can define your own carrier for prices.
The system is able to add and compute the shipping line.
""",
    'depends': ['sale', 'payment_custom'],
    'data': [
        'data/delivery_data.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on `payment_method_cash_on_delivery`.

        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        'report/ir_actions_report_templates.xml',

        'views/delivery_carrier_views.xml',
        'views/delivery_price_rule_views.xml',
        'views/delivery_zip_prefix_views.xml',
        'views/ir_module_module_views.xml',
        'views/payment_form_templates.xml',
        'views/payment_provider_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',

        'wizard/res_config_settings_views.xml',
        'wizard/choose_delivery_carrier_views.xml',
    ],
    'demo': ['data/delivery_demo.xml'],
    'assets': {
        'web.assets_frontend': [
            'delivery/static/src/**/*',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
