# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Chile - Accounting Reports',
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'author': 'CubicERP, Blanco Martin y Asociados',
    'description': """
Accounting reports for Chile
    """,
    'depends': [
        'l10n_cl', 'account_reports',
    ],
    'data': [
        'views/res_config_settings_view.xml',
        'data/eightcolumns_report.xml',
        'data/f29_report.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_cl', 'account_reports'],
    'website': 'http://cubicERP.com',
    'license': 'OEEL-1',
}
