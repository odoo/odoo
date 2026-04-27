# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sweden - SIE 4 Export',
    'summary': 'Export Accounting Data to SIE 4 files',
    'version': '1.0',
    'description': """
        Module for the export of accounting data to SIE 4 standard files.
        Official website: https://sie.se/
        XSD and documentation: https://sie.se/format/
    """,
    'category': "Accounting/Accounting",
    'depends': [
        'account_base_import',
        'account_reports',
        'l10n_se',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
