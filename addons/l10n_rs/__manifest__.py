# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Serbia - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['rs'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module of the Serbian localization. It manages chart of accounts and taxes.
This module is based on the official document "Pravilnik o kontnom okviru i sadržini računa u kontnom okviru za privredna društva, zadruge i preduzetnike ("Sl. glasnik RS", br. 89/2020)"
Source: https://www.paragraf.rs/propisi/pravilnik-o-kontnom-okviru-sadrzini-racuna-za-privredna-drustva-zadruge.html
    """,
    'author': 'Modoolar, Odoo S.A.',
    'depends': [
        'account',
        'base_vat',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'data/menuitem_data.xml',
        'views/account_move.xml',
        'views/report_invoice.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
