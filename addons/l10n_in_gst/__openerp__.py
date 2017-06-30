# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Accounting(GST)',
    'version': '3.0',
    'description': """GST Indian Accounting""",
    'category': 'Localization',
    'depends': [
        'l10n_in',
        'base_vat',
    ],
    'data': [
        'data/account_data.xml',
        'data/account_tax_data.xml',
        'data/account_fiscal_position_data.xml',
        'data/ir_model_fields_data.xml',
        'views/account_financial_report_data.xml',
        'views/product_template_view.xml',
        'views/report_invoice.xml',
        'views/report_templates.xml',
        'views/res_company_view.xml',
        'views/res_partner_views.xml',
        'wizard/account_report_tax_payable_view.xml',
    ],
    'installable': True,
    'application': True,

}
