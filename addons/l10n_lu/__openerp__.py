# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2011 Thamini S.à.R.L (<http://www.thamini.com>)
# Copyright (C) 2011 ADN Consultants S.à.R.L (<http://www.adn-luxembourg.com>)

{
    'name': 'Luxembourg - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Luxembourg.
======================================================================

    * the Luxembourg Official Chart of Accounts (law of June 2009 + 2011 chart and Taxes),
    * the Tax Code Chart for Luxembourg
    * the main taxes used in Luxembourg
    * default fiscal position for local, intracom, extracom """,
    'author': 'OpenERP SA & ADN',
    'website': 'http://www.openerp.com http://www.adn-luxembourg.com',
    'depends': ['account', 'base_vat', 'base_iban'],
    'data': [
        # basic accounting data
        'account_financial_report.xml',
        'account_financial_report_abr.xml',
        'account.account.type-2011.csv',
        'account.account.template-2011.csv',
        'account_chart_template.xml',
        'account.tax.template-2011.csv',
        # Change BRE: adds fiscal position
        'account.fiscal.position.template-2011.csv',
        'account.fiscal.position.tax.template-2011.csv',
        # configuration wizard, views, reports...
        'l10n_lu_wizard.xml',
    ],
    'test': [],
    'demo': [],
    'installable': False,
    'auto_install': False,
}
