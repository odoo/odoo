# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Luxembourg - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/luxembourg.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['lu'],
    'version': '2.2',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Luxembourg.
======================================================================

    * the Luxembourg Official Chart of Accounts (law of June 2009 + 2015 chart and Taxes),
    * the Tax Code Chart for Luxembourg
    * the main taxes used in Luxembourg
    * default fiscal position for local, intracom, extracom

Notes:
    * the 2015 chart of taxes is implemented to a large extent,
      see the first sheet of tax.xls for details of coverage
    * to update the chart of tax template, update tax.xls and run tax2csv.py
""",
    'author': 'Odoo S.A., ADN, ACSONE SA/NV',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
        'account_edi_ubl_cii',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account.account.tag.csv',
        'data/l10n_lu_chart_data.xml',
        'data/tax_report/section_1.xml',
        'data/tax_report/section_2.xml',
        'data/tax_report/sections_34.xml',
        'data/tax_report/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'license': 'LGPL-3',
}
