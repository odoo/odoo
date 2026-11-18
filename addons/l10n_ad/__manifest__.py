# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Andorra - Accounting',
    'summary': ('Creation of account groups, general chart of accounts'
                ' and Andorran taxes (IGI, IRPF)'),
    'version': '1.0.0',
    'countries': ['ad'],
    'author': 'Batista10 <https://batista10.cat>',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Andorran Charts of Accounts
===========================

    * Creation of account groups
    * Creation of general chart of accounts
    * Creation of Andorran taxes (IGI, IRPF)
""",
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
        'data/res_partner_data.xml',
    ],
    'license': 'LGPL-3',
}
