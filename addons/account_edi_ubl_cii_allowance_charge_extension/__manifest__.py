# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Allowance/Charge extension for UBL/CII',
    'version': '1.0',
    'summary': 'Allowance/Charge extension for UBL/CII',
    'description': """
    """,
    'category': 'Accounting/Accounting',
    'website': 'https://www.odoo.com/app/invoicing',
    'depends': ['account_edi_ubl_cii_tax_extension'],
    'data': [
        'views/account_tax_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
