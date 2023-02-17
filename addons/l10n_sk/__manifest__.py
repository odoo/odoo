# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Slovak - Accounting',
    'version': '1.0',
    'author': '26HOUSE',
    'website': 'http://www.26house.com',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Slovakia accounting chart and localization: Chart of Accounts 2020, basic VAT rates + 
fiscal positions.

Tento modul definuje:
• Slovenskú účtovú osnovu za rok 2020

• Základné sadzby pre DPH z predaja a nákupu

• Základné fiškálne pozície pre slovenskú legislatívu

 
Pre viac informácií kontaktujte info@26house.com alebo navštívte https://www.26house.com.
    
    """,
    'depends': [
        'base_iban',
        'base_vat',
        'account',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
