# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Serbia - Accounting",
    "version": "1.0",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
        This is the base module of the Serbian localization. It manages chart of accounts and taxes.
        This module is based on the official document "Pravilnik o kontnom okviru i sadržini računa u kontnom okviru za privredna društva, zadruge i preduzetnike ("Sl. glasnik RS", br. 89/2020)"
        Source: https://www.paragraf.rs/propisi/pravilnik-o-kontnom-okviru-sadrzini-racuna-za-privredna-drustva-zadruge.html
    """,
    "author": "Modoolar, Odoo S.A.",
    "depends": ["account", "base_vat", 'l10n_multilang'],
    "data": [
        "data/account_chart_template_data.xml",
        "data/account.account.template.csv",
        "data/l10n_rs_chart_data.xml",
        "data/account_tax_group_data.xml",
        'data/account_tax_report_data.xml',
        "data/account_tax_template_data.xml",
        "data/fiscal_position_data.xml",
        "data/account.group.template.csv",
        "data/account_chart_template_configure_data.xml",
        "data/menuitem_data.xml",
        "views/account_move.xml",
        "views/report_invoice.xml",
    ],
    "demo": ["demo/demo_company.xml"],
    "license": "LGPL-3",
}
