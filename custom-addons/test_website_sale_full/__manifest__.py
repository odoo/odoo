# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Website Sale Full Tests",
    'summary': "Test Suite for eCommerce functionalities in enterprise",
    'category': "Hidden",
    'depends': [
        'website_sale_comparison',
        'website_sale_renting',
        'website_sale_wishlist',
    ],
    'assets': {
        'web.assets_tests': [
            'test_website_sale_full/static/tests/tours/**/*',
        ],
    },
    'license': 'OEEL-1',
}
