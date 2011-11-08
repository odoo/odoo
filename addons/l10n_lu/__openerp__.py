# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Luxembourg - Plan Comptable Minimum Normalise',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Luxembourg.
======================================================================

    * the KLUWER Chart of Accounts,
    * the Tax Code Chart for Luxembourg
    * the main taxes used in Luxembourg""",
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['account', 'base_vat', 'base_iban'],
    'init_xml': [],
    'update_xml': [
        'account.tax.code.template.csv',
        'l10n_lu_data.xml',
        'l10n_lu_wizard.xml',
        'account.tax.template.csv',
        'wizard/print_vat_view.xml'
    ],
    'test': ['test/l10n_lu_report.yml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0078164766621',
    'images': ['images/config_chart_l10n_lu.jpeg','images/l10n_lu_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
