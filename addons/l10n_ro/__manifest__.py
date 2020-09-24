# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# @author -  Fekete Mihai <feketemihai@gmail.com>, Tatár Attila <atta@nvm.ro>
# Copyright (C) 2019 NextERP Romania (https://nexterp.ro)
# Copyright (C) 2015 Tatár Attila
# Copyright (C) 2015 Forest and Biomass Services Romania (http://www.forbiom.eu).
# Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
# Copyright (C) 2009 (<http://www.filsystem.ro>)

{
    "name": "Romania - Accounting",
    "author": "Fekete Mihai (NextERP Romania SRL)",
    "website": "https://www.nexterp.ro",
    'category': 'Accounting/Localizations/Account Charts',
    "depends": [
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
             'data/account.group.template.csv',
             'data/account.account.template.csv',
             'data/l10n_ro_chart_post_data.xml',
             'data/account_data.xml',
             'data/account_tax_report_data.xml',
             'data/account_tax_data.xml',
             'data/account_fiscal_position_data.xml',
             'data/account_reconcile_model_template_data.xml',
             'data/account_chart_template_data.xml',
             'data/res.bank.csv',
             ],
    'demo': [
        'demo/demo_company.xml',
    ],
}
