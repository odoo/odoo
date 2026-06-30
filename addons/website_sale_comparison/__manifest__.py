# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Comparison',
    'summary': 'Allow shoppers to compare products based on their attributes',
    'description': """
This module adds a comparison tool to your eCommerce shop, so that your shoppers can easily compare products based on their attributes. It will considerably accelerate their purchasing decision.

To configure product attributes, activate *Attributes & Variants* in the Website settings. This will add a dedicated section in the product form. In the configuration, this module adds a category field to product attributes in order to structure the shopper's comparison table.

Finally, the module comes with an option to display an attribute summary table in product web pages (available in Customize menu).
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/website_sale_comparison_template.xml',
        'views/website_sale_comparison_view.xml',
    ],
    'demo': [
        'data/website_sale_comparison_data.xml',
        'data/website_sale_comparison_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'website_sale_comparison/static/src/interactions/**/*',
            'website_sale_comparison/static/src/scss/website_sale_comparison.options.scss',
            'website_sale_comparison/static/src/scss/website_sale_comparison.scss',
            'website_sale_comparison/static/src/js/**/*',
        ],
        'web.assets_tests': [
            'website_sale_comparison/static/tests/**/*',
        ],
        'website.website_builder_assets': [
            'website_sale_comparison/static/src/website_builder/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
