# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Vietnam - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['vn'],
    'version': '2.0.2',
    'author': 'General Solutions',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/vietnam.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the module to manage the accounting chart, bank information for Vietnam in Odoo.
========================================================================================

- This module applies to companies based in Vietnamese Accounting Standard (VAS)
  with Chart of account under Circular No. 200/2014/TT-BTC
- Add Vietnamese bank information (like name, bic ..) as announced and yearly updated by State Bank
  of Viet Nam (https://sbv.gov.vn/webcenter/portal/en/home/sbv/paytreasury/bankidno).
- Add VietQR feature for invoice

**Credits:**
    - General Solutions.
    - Trobz
    - Jean Nguyen - The Bean Family (https://github.com/anhjean/vietqr) for VietQR.

""",
    'depends': [
        'account_qr_code_emv',
        'base_iban',
    ],
    'data': [
        'data/account_tax_report_data.xml',
        'views/res_bank_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
