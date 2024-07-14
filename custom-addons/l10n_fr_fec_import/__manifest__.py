# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "France - FEC Import",
    'countries': ['fr'],
    "summary": "Import Accounting Data from FEC files",
    "description": """
Module for the import of FEC standard files, useful for importing accounting history.

FEC files (fichier des écritures comptables) are the standard accounting reports that French businesses have to submit to the tax authorities.
This module allows the import of accounts, journals, partners and moves from these files.

Only the CSV format of FEC is implemented.
'utf-8', 'utf-8-sig' and 'iso8859_15' are the only allowed encodings.
Several delimiters are allowed: ';' or '|' or ',' or '\t'.

Official Technical Specification (fr)
https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000027804775/

FEC Testing tool from the tax authorities
https://github.com/DGFiP/Test-Compta-Demat

    """,
    "category": "Accounting/Accounting",
    "depends": ["account_accountant", "base_vat", "l10n_fr", "l10n_fr_fec", "account_base_import"],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'l10n_fr_fec_import/static/src/xml/**/*',
        ],
    },
}
