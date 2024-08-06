# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Luxembourg - Peppol Identifier",
    'version': '1.0',
    'description': """
    Some Luxembourg public institutions do not have a VAT number but have been assigned an arbitrary number 
    (see: https://pch.gouvernement.lu/fr/peppol.html). Thus, this module adds the Peppol Identifier field on 
    the account.move form view. If this field is set, it is then read when exporting electronic invoicing formats.
    """,
    'depends': ['l10n_lu', 'account_edi_ubl_cii'],
    'data': [
        'views/partner_view.xml',
    ],
    'license': 'LGPL-3',
}
