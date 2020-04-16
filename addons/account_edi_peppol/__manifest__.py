# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'PEPPOL support for Accounting',
    'description': '''
    Support for invoice Export/Import in Peppol BIS3 format (OpenPeppol Invoice 3.10.1 aka BIS Billing 3.0.7).
    ''',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account_edi_ubl'],
    'data': [
        'data/account_edi_data.xml',
        'data/peppol_ubl_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
