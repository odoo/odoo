# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sweden - SIE 5 Import',
    'countries': ['se'],
    'summary': 'Import Accounting Data from SIE 5 files',
    'version': '1.0',
    'description': """
        Module for the import of SIE 5 standard files.

        The current scope of the module will allow the initialization of the accounting by importing account balances,
        partners (Customers & Suppliers), and journal entries (journal data must be present in the file).

        It doesn't import analytics, assets, and "accounts linkage" data.

        Official website: https://sie.se/
        XSD and documentation: https://sie.se/format/
    """,
    'category': "Accounting/Accounting",
    'depends': [
        'account_base_import',
        'l10n_se',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/l10n_se_sie_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_se_sie_import/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
    'installable': True,
}
