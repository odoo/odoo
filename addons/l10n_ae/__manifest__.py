# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'U.A.E. - Accounting',
    'author': 'Tech Receptives',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
United Arab Emirates accounting chart and localization.
=======================================================
    """,
    'depends': ['base', 'account'],
    'data': [
        'data/l10n_ae_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_chart_template_data.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
