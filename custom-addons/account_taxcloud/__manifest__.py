# -*- coding: utf-8 -*-
{
    'name': "Account TaxCloud",
    'summary': """TaxCloud make it easy for business to comply with sales tax law""",
    'description': """
Computes the sales tax automatically using TaxCloud and the customer's address in United States.
    """,
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['l10n_us'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_fiscal_position_view.xml',
        'views/product_view.xml',
        'views/res_config_settings_views.xml',
        'views/account_invoice_views.xml',
        'data/account_taxcloud_data.xml',
    ],
    'license': 'OEEL-1',
    'pre_init_hook': 'pre_init_hook',
}
