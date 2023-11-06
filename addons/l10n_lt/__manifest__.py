# Author: Silvija Butko. Copyright: JSC Focusate.
# Co-Authors: Eimantas Nėjus, Andrius Laukavičius. Copyright: JSC Focusate
# See LICENSE file for full copyright and licensing details.
{
    'name': "Lithuania - Accounting",
    'version': '1.1',
    'description': """
        Chart of Accounts (COA) Template for Lithuania's Accounting.

        This module also includes:

        * List of available banks in Lithuania.
        * Tax groups.
        * Most common Lithuanian Taxes.
        * Fiscal positions.
        * Account Tags.
    """,
    'license': 'LGPL-3',
    'author': "Focusate",
    'website': "http://www.focusate.eu",
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'l10n_multilang',
    ],
    'data': [
        'data/account_account_tag_data.xml',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_setup_data.xml',
        'data/res_bank_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_template_data.xml',
        # Try Loading COA for Current Company
        'data/account_chart_template_load.xml',
        'data/menuitem_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
    'installable': True,
}
