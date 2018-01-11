# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Intrastat Declaration',
    'category': 'Localization',
    'description': """
Generates Intrastat XML report for declaration
Based on invoices.
    """,
    'depends': ['account_intrastat'],
    'data': [
        'data/l10n_be_intrastat_chart_data.xml',
        'security/l10n_be_intrastat_security.xml',
        'views/res_users_views.xml',
    ],
}
