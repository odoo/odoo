# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales',
    'version': '1.0',
    'category': 'Sales/Sales',
    'sequence': 5,
    'summary': 'From quotations to invoices',
    'description': """
Manage sales quotations and orders
==================================

This application allows you to manage your sales goals in an effective and efficient manner by keeping track of all sales orders and history.

It handles the full sales workflow:

* **Quotation** -> **Sales order** -> **Invoice**

Preferences (only with Warehouse Management installed)
------------------------------------------------------

If you also installed the Warehouse Management, you can deal with the following preferences:

* Shipping: Choice of delivery at once or partial delivery
* Invoicing: choose how invoices will be paid
* Incoterms: International Commercial terms


With this module you can personnalize the sales order and invoice report with
categories, subtotals or page-breaks.

The Dashboard for the Sales Manager will include
------------------------------------------------
* My Quotations
* Monthly Turnover (Graph)
    """,
    'website': 'https://www.odoo.com/app/sales',
    'depends': ['sale', 'digest'],
    'data': [
        'data/digest_data.xml',

        'security/ir.model.access.csv',
        'security/sale_management_security.xml',

        # Define SO template views & actions before their place of use
        'views/sale_order_template_views.xml',

        'views/digest_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/sale_portal_templates.xml',

        'views/sale_management_menus.xml',
    ],
    'demo': [
        'data/sale_order_template_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_management/static/src/fields/**/*',
        ],
        'web.assets_frontend': [
            'sale_management/static/src/interactions/**/*',
        ],
        'web.assets_tests': [
            'sale_management/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'sale_management/static/tests/**/*.test.js',
        ],
    },
    'application': True,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
