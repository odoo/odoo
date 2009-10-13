# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Luxembourg - Plan Comptable Minimum Normalise',
    'version': '1.0',
    'category': 'Localisation/Account Charts',
    'description': """
This module installs:

    *the KLUWER Chart of Accounts,
    *the Tax Code Chart for Luxembourg
    *the main taxes used in Luxembourg""",
    'author': 'Tiny',
    'website': 'http://openerp.com',
    'depends': ['account', 'account_report', 'base_vat', 'base_iban'],
    'init_xml': [],
    'update_xml': [
        'account.tax.code.template.csv',
        'l10n_lu_data.xml',
        'account.tax.template.csv',
        'l10n_lu_wizard.xml',
        'l10n_lu_report.xml'
    ],
    'demo_xml': ['account.report.report.csv'],
    'installable': True,
    'certificate': '0078164766621',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
