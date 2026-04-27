{
    'name': 'Dominican Republic - Checks Layout',
    'version': '1.0',
    'category': 'Accounting/Localizations/Check',
    'summary': 'Print Dominican Republic Checks',
    'description': """
This module allows to print your payments on pre-printed check paper.
You can configure the output (layout, stubs information, etc.) in company settings, and manage the
checks numbering (if you use pre-printed checks without numbers) in journal settings.

Supported formats
-----------------
Three layouts copied from the US check printing module, adjusted for DO
    """,
    'website': 'https://www.odoo.com/app/accounting',
    'depends': ['account_check_printing', 'l10n_do'],
    'data': [
        'data/do_check_printing.xml',
        'report/print_check.xml',
        'report/print_check_templates.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_do'],
    'license': 'OEEL-1',
    'assets': {
        'web.report_assets_common': [
            'l10n_do_check_printing/static/src/scss/report_check_commons.scss',
            'l10n_do_check_printing/static/**/*',
        ],
    }
}
