# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tax extension for UBL/CII',
    'version': '1.0',
    'summary': 'Tax extension for UBL/CII',
    'description': """
    This module adds 2 useful fields on the taxes for electronic invoicing: the tax category code and the tax exemption reason code.
    These fields will be read when generating Peppol Bis 3 or Factur-X xml, for instance.
    """,
    'category': 'Accounting/Accounting',
    'website': 'https://www.odoo.com/app/invoicing',
    'depends': ['account_edi_ubl_cii'],
    'data': [
        'views/account_tax_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
