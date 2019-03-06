# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# @author -  Fekete Mihai <feketemihai@gmail.com>, Tatár Attila <atta@nvm.ro>
# Copyright (C) 2015 Tatár Attila
# Copyright (C) 2015 Forest and Biomass Services Romania (http://www.forbiom.eu).
# Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
# Copyright (C) 2009 (<http://www.filsystem.ro>)

{
    "name" : "Romania - Accounting",
    "author" : "Fekete Mihai (Forest and Biomass Services Romania)",
    "website": "http://www.forbiom.eu",
    'category': 'Localization',
    "depends" : [
        'account',
        'base_vat',
    ],
    "description": """
This is the module to manage the Accounting Chart, VAT structure, Fiscal Position and Tax Mapping.
It also adds the Registration Number for Romania in Odoo.
================================================================================================================

Romanian accounting chart and localization.
    """,
    "data": ['views/res_partner_view.xml',
             'data/l10n_ro_chart_data.xml',
             'data/account.account.template.csv',
             'data/l10n_ro_chart_post_data.xml',
             'data/account_data.xml',
             'data/account_tax_data.xml',
             'data/account_fiscal_position_data.xml',
             'data/account_chart_template_data.xml',
             'data/res.country.state.csv',
             'data/res.bank.csv',
             ],
}
