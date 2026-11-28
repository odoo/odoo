# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Monaco - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mc'],
    'version': '1.1',
    'author': 'Odoo S.A.',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Monaco.
==================================================================

Monegasque companies keep their books according to the French general chart of accounts
(Plan Comptable Général), adapted to Monaco: Monegasque social funds (CCSS, CAR, CMRC), corporate
income tax (ISB), and no French-only accounts.

Monaco and France form a single VAT territory (Franco-Monegasque customs convention of 1963): the VAT
rates are the French ones and the operations with France are domestic. The taxes are reported on the
VAT return of the Direction des Services Fiscaux, including the breakdown of the deductible VAT by
origin of the invoices (box C).
""",
    'depends': [
        'l10n_fr_account',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
