# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# @author -  Fekete Mihai <feketemihai@gmail.com>
# Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.www.erpsystems.ro).
# Copyright (C) 2009 (<http://www.filsystem.ro>)

{
    "name" : "Romania - Accounting",
    "version" : "1.0",
    "author" : "ERPsystems Solutions",
    "website": "http://www.erpsystems.ro",
    "category" : "Localization/Account Charts",
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
              'account_chart_template.xml',
              'account_tax_template.xml',
              'fiscal_position_template.xml',
              'l10n_chart_ro_wizard.xml',
              ],
    "installable": False,
}
