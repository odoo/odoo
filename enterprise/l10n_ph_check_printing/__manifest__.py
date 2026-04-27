{
    'name': 'Philippines Checks Layout',
    'version': '1.0',
    'category': 'Accounting/Localizations/Check',
    'summary': 'Print PH Checks',
    'description': """
This module allows to print your payments on pre-printed checks.
    """,
    'website': 'https://www.odoo.com/app/accounting',
    'depends': ['account_check_printing', 'l10n_ph'],
    'data': [
        'data/ph_check_printing.xml',
        'report/print_check.xml',
        'views/res_config_settings_view.xml',
        'views/account_payment_views.xml',
        'views/account_menuitem.xml',
    ],
    'auto_install': ['l10n_ph'],
    'license': 'OEEL-1',
    'assets': {
        'web.report_assets_common': [
            'l10n_ph_check_printing/static/**/*',
        ],
    }
}
