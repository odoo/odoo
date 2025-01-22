# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Malaysia - E-invoicing Extended Features',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    "summary": "Extended features for the E-invoicing using MyInvois",
    'description': """
    This module improves the MyInvois E-invoicing feature by adding proper support for self billing, rendering the MyInvois
    QR code in the invoice PDF file and allows better management of foreign customer TIN.
    """,
    'depends': ['l10n_my_edi'],
    'data': [
        'views/account_move_view.xml',
        'views/report_invoice.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_my_edi'],
    'license': 'LGPL-3'
}
