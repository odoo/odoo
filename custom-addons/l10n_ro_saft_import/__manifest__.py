# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Romania - SAF-T Import",
    'countries': ['ro'],
    "summary": "Import Accounting Data from SAF-T files",
    "description": """
Module for the import of SAF-T files for Romania, useful for importing accounting history.
Adds specificities for the Romanian SAF-T

    """,
    "category": "Accounting/Localizations",
    "depends": ["account_saft_import", "l10n_ro_saft"],
    'license': 'OEEL-1',
    'auto_install': True,
}
