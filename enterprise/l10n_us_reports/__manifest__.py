# -*- coding: utf-8 -*-
{
    'name': 'US - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for US
    """,
    'website': 'https://www.odoo.com/app/accounting',
    'depends': [
        'l10n_us', 'account_reports'
    ],
    'data': [
        'data/check_register.xml',
    ],
    'installable': True,
    'post_init_hook': '_l10n_us_reports_post_init',
    'auto_install': ['l10n_us', 'account_reports'],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'l10n_us_reports/static/src/components/check_register/**/*',
        ],
    }
}
