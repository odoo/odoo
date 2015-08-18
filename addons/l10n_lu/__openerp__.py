# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2011 Thamini S.à.R.L (<http://www.thamini.com>)
#    Copyright (C) 2011 ADN Consultants S.à.R.L (<http://www.adn-luxembourg.com>)
#    Copyright (C) 2012-today OpenERP SA (<http://openerp.com>)
#    Copyright (C) 2014 ACSONE SA/NV (<http://acsone.eu>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Luxembourg - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
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
    'website': 'https://www.odoo.com',
    'depends': ['account', 'base_vat', 'base_iban'],
    'data': [
        # basic accounting data
        'account_financial_report.xml',
        'account_financial_report_abr.xml',
        'account.account.type-2011.csv',
        'account.account.template-2011.csv',
        'account.tax.code.template-2015.csv',
        'account_chart_template.xml',
        'account.tax.template-2015.csv',
        'account.fiscal.position.template-2011.csv',
        'account.fiscal.position.tax.template-2015.csv',
        # configuration wizard, views, reports...
        'l10n_lu_wizard.xml',
    ],
    'test': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
