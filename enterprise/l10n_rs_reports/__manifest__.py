## -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Serbia - Accounting Reports',
    'version': '1.0',
    'description': """
Accounting reports for Serbia.
This module is based on the official document "Pravilnik o kontnom okviru i sadržini računa u kontnom okviru za privredna društva, zadruge i preduzetnike ("Sl. glasnik RS", br. 89/2020)"
Source: https://www.paragraf.rs/propisi/pravilnik-o-kontnom-okviru-sadrzini-racuna-za-privredna-drustva-zadruge.html
    """,
    "author": "Modoolar, Odoo S.A.",
    'category': 'Accounting/Localizations/Reporting',
    'depends': [
        'l10n_rs',
        'account_reports',
    ],
    'data': [
        'data/profit_and_loss.xml',
        'data/balance_sheet.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
