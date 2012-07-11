# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2011 Thamini S.à.R.L (<http://www.thamini.com>)
#    Copyright (C) 2011 ADN Consultants S.à.R.L (<http://www.adn-luxembourg.com>)
#    Copyright (C) 2012-today OpenERP SA (<http://openerp.com>)
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

    * the Luxembourg Official Chart of Accounts (law of June 2009 + 2011 chart and Taxes),
    * the Tax Code Chart for Luxembourg
    * the main taxes used in Luxembourg
    * default fiscal position for local, intracom, extracom """,
    'author': 'OpenERP SA & ADN',
    'website': 'http://www.openerp.com http://www.adn-luxembourg.com',
    'depends': ['account', 'base_vat', 'base_iban'],
    'init_xml': [],
    'update_xml': [
        # basic accounting data
        #'account.account.type-2009.csv',
        'account.account.type-2011.csv',
        # memorial 2009 account chart - required for 2011+
        # Change BRE to activate taxes and accounts 2011
        #'account.account.template-2009.csv',
        'account.account.template-2011.csv',
        'account.tax.code.template-2011.csv',
        #'account.chart.template-2009.csv',
        'account.chart.template-2011.csv',
        'account.tax.template-2011.csv',
        # Change BRE: adds fiscal position
        'account.fiscal.position.template-2011.csv',
        'account.fiscal.position.tax.template-2011.csv',
        # configuration wizard, views, reports...
        'l10n_lu_wizard.xml',
        'account.tax.template.csv',
        'l10n_lu_view.xml',
        'wizard/print_vat_view.xml'
    ],
    'test': ['test/l10n_lu_report.yml'],
    'demo_xml': [],
    'installable': True,
    'auto_install': False,
    'certificate': '0078164766621',
    'images': ['images/config_chart_l10n_lu.jpeg','images/l10n_lu_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
