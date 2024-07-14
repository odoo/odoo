# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'UK BACS Payment Files',
    'summary': """Export payments as BACS Direct Debit and Direct Credit files""",
    'category': 'Accounting/Accounting',
    'description': """
This module enables generating payment orders as required by the BACS Direct Debit and Direct Credit standards. The generated plain text files can then be uploaded to your bank for processing.

Direct Debit allows businesses to collect payments directly from the bank accounts of customers, whereas the Direct Credit functionality enables businesses to make payments directly to bank accounts of individuals or other businesses.

This module follows the implementation guidelines issued by the Bacs Payment Schemes Limited (BPSL). For more information about the BACS standards: https://www.bacs.co.uk/
    """,
    'version': '1.0',
    'depends': ['account_batch_payment', 'base_iban'],
    'data': [
        'security/ir.model.access.csv',
        'report/ddi_report.xml',
        'data/bacs_payment_methods.xml',
        'views/bacs_ddi_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_payment_views.xml',
        'views/account_batch_payment_views.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'account_bacs/static/src/scss/**/*',
        ],
    },
    'license': 'OEEL-1',
}
