# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2009 - now Grzegorz Grzelak grzegorz.grzelak@openglobe.pl

{
    'name' : 'Poland - Accounting',
    'version' : '1.02',
    'author' : 'Grzegorz Grzelak (OpenGLOBE)',
    'website': 'http://www.openglobe.pl',
    'category' : 'Localization/Account Charts',
    'description': """
This is the module to manage the accounting chart and taxes for Poland in OpenERP.
==================================================================================

To jest moduł do tworzenia wzorcowego planu kont, podatków, obszarów podatkowych i
rejestrów podatkowych. Moduł ustawia też konta do kupna i sprzedaży towarów
zakładając, że wszystkie towary są w obrocie hurtowym.

Niniejszy moduł jest przeznaczony dla odoo 8.0.
Wewnętrzny numer wersji OpenGLOBE 1.02
    """,
    'depends' : ['account', 'base_iban', 'base_vat'],
    'demo' : [],
    'data' : [
              'account_chart.xml',
              'account_tax.xml',
              'fiscal_position.xml',
              'country_pl.xml',
              'account_chart_template.yml'
    ],
    'installable': True,
}
