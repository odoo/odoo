# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# @author -  Fekete Mihai <feketemihai@gmail.com>, Tatár Attila <atta@nvm.ro>
# Copyright (C) 2015 Tatár Attila
# Copyright (C) 2015 Forest and Biomass Services Romania (http://www.forbiom.eu).
# Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
# Copyright (C) 2009 (<http://www.filsystem.ro>)

{
    "name" : "Romania - Accounting",
    "version" : "1.0",
    "author" : "Fekete Mihai (Forest and Biomass Services Romania)",
    "website": "http://www.forbiom.eu",
    'category': 'Localization',
    "depends" : ['account','base_vat'],
    "description": """
This is the module to manage the Accounting Chart, VAT structure, Fiscal Position and Tax Mapping.
It also adds the Registration Number for Romania in OpenERP.
================================================================================================================

Romanian accounting chart and localization.
    """,
    "demo" : [],
    "data" : ['partner_view.xml',
              'account_chart.xml',
              'account_tax_template.xml',
              'fiscal_position_template.xml',
              'account_chart_template.yml',
              'res.country.state.csv',
              'res.bank.csv',
              ],
    "installable": True,
}
