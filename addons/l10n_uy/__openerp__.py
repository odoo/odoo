# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011 Openerp.uy <openerp.uy@lists.launchpad.net>
#                  Proyecto de Localización de OperERP para Uruguay
#    $Id$
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
    'name' : 'Uruguay - Chart of Accounts',
    'version' : '0.1',
    'author' : 'Uruguay l10n Team & Guillem Barba',
    'category' : 'Localization/Account Charts',
    'website' : 'https://launchpad.net/openerp-uruguay',
    'description': """
General Chart of Accounts.
==========================

Provide Templates for Chart of Accounts, Taxes for Uruguay.

""",
    'license'   : 'AGPL-3',
    'depends'   : [
                    'account',
                  ],
    'data': [
                    'account_types.xml',
                    'taxes_code_template.xml',
                    'account_chart_template.xml',
                    'taxes_template.xml',
                    'l10n_uy_wizard.xml',
                  ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'certificate' : '0078287892698',
    'images': ['images/config_chart_l10n_uy.jpeg','images/l10n_uy_chart.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
