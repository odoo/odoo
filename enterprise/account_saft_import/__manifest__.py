# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SAF-T Import',
    'summary': 'Import Accounting Data from SAF-T files',
    'description': """
Module for the import of SAF-T files, useful for importing accounting history.

SAF-T files are the standard accounting reports that businesses in some countries have to submit to the tax authorities.
This module allows the import of accounts, journals, partners, taxes and moves from these files.
    """,
    'depends': [
        'account_saft',
        'account_base_import',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_saft_import/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
}
