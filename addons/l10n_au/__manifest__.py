# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Australia - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/australia.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['au'],
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Australian Accounting Module
============================

Australian accounting basic charts and localizations.

Also:
    - activates a number of regional currencies.
    - sets up Australian taxes.
    """,
    'depends': ['account'],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/bas_a.xml',
        'data/bas_c.xml',
        'data/bas_d.xml',
        'data/bas_f.xml',
        'data/bas_g.xml',
        'data/bas_u.xml',
        'data/bas_v.xml',
        'data/bas_w.xml',
        'data/bas_x.xml',
        'data/bas_y.xml',
        'data/master_bas.xml',
        'data/res_currency_data.xml',
        'data/account.account.tag.csv',
        'views/menuitems.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
        'views/res_partner_bank_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/res_bank.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
