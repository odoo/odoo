# -*- coding: utf-8 -*-
{
    'name': 'Canadian Checks Layout',
    'version': '1.0',
    'author': 'Odoo SA, OERP Canada',
    'category': 'Accounting/Localizations/Check',
    'summary': 'Print CA Checks',
    'description': """
This module allows to print your payments on pre-printed checks.
You can configure the output (layout, stubs, paper format, etc.) in company settings, and manage the
checks numbering (if you use pre-printed checks without numbers) in journal settings.
As per Canadian Payment Association (https://www.payments.ca/sites/default/files/standard_006_complete_0.pdf)

Supported formats
-----------------
- Check on top: Quicken / QuickBooks standard
- Check on middle: Peachtree standard
- Check on bottom: ADP standard
    """,
    'website': 'https://www.odoo.com/app/accounting',
    'depends': ['account_check_printing', 'l10n_ca'],
    'data': [
        'data/ca_check_printing.xml',
        'report/print_check.xml',
        'report/print_check_top.xml',
        'report/print_check_middle.xml',
        'report/print_check_bottom.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_ca'],
    'license': 'OEEL-1',
    'assets': {
        'web.report_assets_common': [
            'l10n_ca_check_printing/static/**/*',
        ],
    }
}
