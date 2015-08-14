# -*- coding: utf-8 -*-
# #############################################################################
#
# First author: Jose Ernesto Mendez <tecnologia@obsdr.com> (Open Business Solutions SRL.)
# Copyright (c) 2012 -TODAY Open Business Solutions, SRL. (http://obsdr.com). All rights reserved.
#
# This is a fork to upgrade to odoo 8.0
# by Marcos Organizador de Negocios - Eneldo Serrata - www.marcos.org.do
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Marcos Organizador de Negocios.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

{
    'name': 'Dominican Republic - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Dominican Republic.
==============================================================================

* Chart of Accounts.
* The Tax Code Chart for Domincan Republic
* The main taxes used in Domincan Republic
* Fiscal position for local """,
    'author': 'Eneldo Serrata - Marcos Organizador de Negocios, SRL.',
    'website': 'http://marcos.do',
    'depends': ['account', 'base_iban'],
    'data': [
        # basic accounting data
        'data/ir_sequence_type.xml',
        'data/ir_sequence.xml',
        'data/account_journal.xml',
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account.tax.code.template.csv',
        'data/account_chart_template.xml',
        'data/account.tax.template.csv',
        'data/l10n_do_base_data.xml',
        # Adds fiscal position
        'data/account.fiscal.position.template.csv',
        'data/account.fiscal.position.tax.template.csv',
        # configuration wizard, views, reports...
        'data/l10n_do_wizard.xml'
    ],
    'test': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
