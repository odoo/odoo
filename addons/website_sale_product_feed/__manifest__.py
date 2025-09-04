# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Google Merchant Center",
    'category': 'Website/Website',
    'sequence': 50,
    'summary': "Synchronize your products with Google Merchant Center",
    'depends': ['website_sale'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/res_groups.xml',

        # Model views.
        'views/gmc_templates.xml',
        'views/product_feed_views.xml',
        'views/website_sale_product_feed_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'post_init_hook': '_post_init_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
