# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2011 Thamini S.à.R.L (<http://www.thamini.com>)
# Copyright (C) 2011 ADN Consultants S.à.R.L (<http://www.adn-luxembourg.com>)
#    Copyright (C) 2014 ACSONE SA/NV (<http://acsone.eu>)

{
    'name': 'Luxembourg - Accounting',
    'version': '2.0',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Luxembourg.
======================================================================

    * the Luxembourg Official Chart of Accounts (law of June 2009 + 2015 chart and Taxes),
    * the Tax Code Chart for Luxembourg
    * the main taxes used in Luxembourg
    * default fiscal position for local, intracom, extracom

Notes:
    * the 2015 chart of taxes is implemented to a large extent,
      see the first sheet of tax.xls for details of coverage
    * to update the chart of tax template, update tax.xls and run tax2csv.py
""",
    'author': 'OpenERP SA, ADN, ACSONE SA/NV',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
        # basic accounting data
        'data/account_financial_report_data.xml',
        'data/account_financial_report_abr_data.xml',
        'data/l10n_lu_chart_data.xml',
        'data/account.account.template-2011.csv',
        'data/account.account.tag.csv',
        'data/account.tax.group.csv',
        'data/account.tax.template-2015.csv',
        'data/account.fiscal.position.template-2011.csv',
        'data/account.fiscal.position.tax.template-2015.csv',
        # configuration wizard, views, reports...
        'data/account.chart.template.csv',
        'data/account_chart_template_data.yml',
    ],
    'post_init_hook': '_preserve_tag_on_taxes',
}
