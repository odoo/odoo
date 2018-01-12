# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - VAT Anti-Fraud Certification for Point of Sale (CGI 286 I-3 bis) Part 2',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This add-on brings the technical requirements of the French regulation CGI art. 286, I. 3° bis that stipulates certain criteria concerning the inalterability, security, storage and archiving of data related to sales to private individuals (B2C).
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Install it if you use the Point of Sale app to sell to individuals.

The module adds following features:

    Inalterability: store all printed tickets in database

    Storage: store POS orders if pro format ticket is printed

    Reports: Show hash on receipts, DUPLICATA on reprinted recceipt and PRO FORMAT on bill
""",
    'depends': ['l10n_fr_pos_cert'],
    'installable': True,
    'auto_install': True,
    'application': False,
    'data': [
            'views/l10n_fr_pos_cert2.xml',
        ],
    'qweb': ['static/src/xml/pos.xml'],
}
