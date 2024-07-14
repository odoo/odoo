# -*- coding: utf-8 -*-
{
    'name': "Account TaxCloud - Ecommerce",
    'summary': """Compute taxes with TaxCloud in eCommerce""",
    'category': 'Accounting/Accounting',
    'depends': ['sale_account_taxcloud', 'website_sale'],
    'data': ['views/templates.xml'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_tests': [
            'website_sale_account_taxcloud/static/tests/**/*',
        ],
    }
}
