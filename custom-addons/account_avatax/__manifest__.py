# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Avatax',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['payment', 'account_external_tax'],
    'data': [
        'security/ir.model.access.csv',
        'data/product.avatax.category.csv',
        'data/fiscal_position.xml',
        'views/account_fiscal_position_views.xml',
        'views/account_move_views.xml',
        'views/avatax_category_views.xml',
        'views/avatax_exemption_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/product_views.xml',
        'wizard/avatax_validate_address_views.xml',
        'wizard/avatax_connection_test_result_views.xml',
        'reports/account_invoice.xml',
    ],
    'license': 'OEEL-1',
}
