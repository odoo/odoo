# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer References',
    'category': 'Website/Website',
    'summary': 'Publish your customer references',
    'description': """
Publish your customers as business references on your website to attract new potential prospects.
    """,
    'depends': [
        'website_crm_partner_assign',
        'website_partner',
        'website_google_map',
    ],
    'demo': [
        'data/res_partner_demo.xml',
    ],
    'data': [
        'views/website_customer_templates.xml',
        'views/res_partner_views.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'website.website_builder_assets': [
            'website_customer/static/src/website_builder/**/*',
        ],
        'web.assets_frontend': [
            'website_customer/static/src/scss/website_customer.scss',
        ],
        'web.assets_tests': [
            'website_customer/static/tests/tours/customer_filter_with_tag.js',
        ],
    },
}
