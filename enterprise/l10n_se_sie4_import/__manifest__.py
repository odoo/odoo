# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sweden - SIE 4 Import',
    'countries': ['se'],
    'summary': 'Import Accounting Data from SIE 4 files',
    'version': '1.0',
    'description': """
        Module for the import of SIE 4 standard files.
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
        'wizard/import_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_se_sie4_import/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
