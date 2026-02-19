# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).
{
    'name': 'Product Brand Manager',
    'version': '16.0.1.0',
    'category': 'Product',
    'summary': "Product Brand Management | Manage Multiple Product Brands | Brand Assignment to Products | Brand Visibility on Website | Brand Filtering in Sales | Product Brand Reports | Comprehensive Brand Management | Enhanced Product Listings | Product Brand Customization | Brand Data Management | Brand Insights and Analytics | Product Branding Features",
    'description': " Manage multiple brands and their products effortlessly. Assign brands to products and allow customers to filter by brand on the shop page.",
    'author': 'Kanak Infosystems LLP.',
    'website': 'https://kanakinfosystems.com',
    'license': 'OPL-1',
    'depends': [
        'sale_management',
        'website_sale'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/product_brand_view.xml',
        'reports/sale_report_view.xml',
        'reports/account_invoice_report_view.xml',
        'views/all_brands.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'product_brand_knk/static/src/scss/custom.scss',
        ],
    },
    'installable': True,
    'auto_install': False
}
