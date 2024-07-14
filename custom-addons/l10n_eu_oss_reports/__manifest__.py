# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'EU One Stop Shop (OSS) Reports',
    'category': 'Accounting/Localizations',
    'description': """
EU One Stop Shop (OSS) VAT Reports
=============================================================================================

Provides Reports for OSS with export files for available EU countries.

    """,
    'depends': ['account_reports', 'l10n_eu_oss'],
    'data': [
        'views/report_export_templates.xml',
        'views/res_company_views.xml',
        'views/product_views.xml',
        'data/account_reports.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
