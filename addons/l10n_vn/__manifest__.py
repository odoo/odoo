# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "Vietnam - Accounting",
    "version": "2.0.1",
    "author": "General Solutions & Jean Nguyen",
    'website': """http://gscom.vn, https://thebeanfamily.org""",
    'category': 'Accounting/Localizations/Account Charts',
    "description": """
This is the module to manage the accounting chart, bank information for Vietnam in Odoo.
===========================================================================================
        
- This module applies to companies based in Vietnamese Accounting Standard (VAS) with Chart of account under Circular No. 200/2014/TT-BTC.
- Add Vietnamese bank information (like name, bic ..) as announced and yearly updated by State Bank of Viet Nam (https://sbv.gov.vn/webcenter/portal/en/home/sbv/paytreasury/bankidno).
        
**Credits:**
    - General Solutions.
    - Trobz
    - Jean Nguyen - The Bean Family
    """,
    "depends": [
        "account",
        "base_iban",
        "l10n_multilang"
    ],
    "data": [
         'data/l10n_vn_chart_data.xml',
         'data/account.account.template.csv',
         'data/l10n_vn_chart_post_data.xml',
         'data/account_tax_group_data.xml',
         'data/account_tax_report_data.xml',
         'data/account_tax_data.xml',
         'data/account_chart_template_data.xml',
         'data/res.bank.csv',
    ],

    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_post_init_hook',

    'license': 'LGPL-3',
}
