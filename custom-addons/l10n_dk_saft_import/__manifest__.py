# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Denmark - SAF-T Import",
    'countries': ['dk'],
    "summary": "Import Accounting Data from SAF-T files",
    "description": """
Module for the import of SAF-T files for Denmark, useful for importing accounting history.
Adds specificities for the Danish SAF-T

Official Technical Specification
https://erhvervsstyrelsen.dk/sites/default/files/2023-01/Technical-description-SAFT-Financial-data-version-1-0-nov2022_U.pdf

    """,
    "category": "Accounting/Localizations",
    "depends": ["account_saft_import", "l10n_dk"],
    'license': 'OEEL-1',
    'auto_install': True,
}
