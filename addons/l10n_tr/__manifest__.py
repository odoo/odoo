{
    'name': 'Türkiye - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['tr'],
    'version': '1.4',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Türkiye in Odoo
==========================================================================

Türkiye accounting basic charts and localizations
-------------------------------------------------
Activates:

- Chart of Accounts
- Taxes
- Tax Report
    """,
    'author': 'Odoo S.A., Drysharks Consulting and Trading Ltd.',
    'depends': [
        'account',
        'contacts',
    ],
    'auto_install': ['account'],
    'data': [
        'security/ir.access.csv',
        'data/account_tax_report_data.xml',
        'data/account_tax_report_stamp_tax.xml',
        'data/l10n_tr.tax.office.csv',
        'views/l10n_tr_tax_office_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_tr/static/src/js/dynamic_list.js',
        ],
    },
    'license': 'LGPL-3',
}
