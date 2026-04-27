# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'French Intrastat Declaration',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Generates Intrastat XML report (DEBWEB2) for declaration based on invoices for France.
    """,
    'depends': ['l10n_fr_account', 'account_intrastat'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_view.xml',
        'data/intrastat_export.xml',
        'data/code_region_data.xml',
        'wizard/export_wizard.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
