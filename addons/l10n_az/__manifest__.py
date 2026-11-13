{
    'name': "Azerbaijan - Accounting",
    'category': "Accounting/Localizations/Account Charts",
    'summary': "Azerbaijani accounting localization package",
    'countries': ['AZ'],
    'description': """
This module provides the basic accounting configuration required to use Odoo Accounting in Azerbaijan, including:
==================================================================================================================
* Azerbaijani chart of accounts
* Tax groups, taxes and tax grids
* Withholding taxes
* Fiscal Positions
* Electronic invoice (E-Qaimə Faktura, EQF) XML export, to be uploaded on the e-taxes.gov.az portal

The module is designed to provide a standard accounting setup for companies operating in Azerbaijan and can be extended further based on specific business or legal requirements.
    """,
    'author': "Odoo S.A.",
    'depends': [
        'account',
        'l10n_account_withholding_tax',
    ],
    'data': [
        'data/account_account_tag_data.xml',
        'data/account_tax_report_withholding_data.xml',
        'data/account_tax_report_tit_data.xml',
        'data/ir_config_parameter_data.xml',
        'security/ir.access.csv',
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'wizard/l10n_az_eqf_error_wizard_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': "LGPL-3",
}
