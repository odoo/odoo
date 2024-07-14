# -*- coding: utf-8 -*-
{
    'name': 'US Checks Layout',
    'countries': ['us'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Check',
    'summary': 'Print US Checks',
    'description': """
This module allows to print your payments on pre-printed check paper.
You can configure the output (layout, stubs information, etc.) in company settings, and manage the
checks numbering (if you use pre-printed checks without numbers) in journal settings.

Supported formats
-----------------
This module supports the three most common check formats and will work out of the box with the linked checks from checkdepot.net.

View all checks at: https://www.checkdepot.net/checks/laser/Odoo.htm

You can choose between:

- Check on top: Quicken / QuickBooks standard (https://www.checkdepot.net/checks/checkorder/laser_topcheck.htm)
- Check on middle: Peachtree standard (https://www.checkdepot.net/checks/checkorder/laser_middlecheck.htm)
- Check on bottom: ADP standard (https://www.checkdepot.net/checks/checkorder/laser_bottomcheck.htm)
    """,
    'website': 'https://www.odoo.com/app/accounting',
    'depends' : ['account_check_printing', 'l10n_us'],
    'data': [
        'data/us_check_printing.xml',
        'report/print_check.xml',
        'report/print_check_top.xml',
        'report/print_check_middle.xml',
        'report/print_check_bottom.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_us'],
    'license': 'OEEL-1',
    'assets': {
        'web.report_assets_common': [
            'l10n_us_check_printing/static/src/scss/report_check_commons.scss',
            'l10n_us_check_printing/static/**/*',
        ],
    }
}
