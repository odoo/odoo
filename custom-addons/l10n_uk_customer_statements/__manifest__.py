# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'UK - Customer Statements',
    'version': '1.0',
    'description': """
This is a bridge module to install the customer statements module by default with the UK localization
    """,
    'summary': "Customer Statements",
    'countries': ['gb'],
    'depends': [
        'l10n_uk',
        'l10n_account_customer_statements'
    ],
    'installable': True,
    'auto_install': ['l10n_uk'],
    'license': 'OEEL-1',
}
