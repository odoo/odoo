# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2009-2010 Salvatore J. Trimarchi <salvatore@trimarchi.co.cc>
# (http://salvatoreweb.co.cc)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#
# This module provides a minimal Honduran chart of accounts that can be use
# to build upon a more complex one.  It also includes a chart of taxes and
# the Lempira currency.
#
# This module is based on the Guatemalan chart of accounts:
# Copyright (c) 2009-2010 Soluciones Tecnologócias Prisma S.A. All Rights Reserved.
# José Rodrigo Fernández Menegazzo, Soluciones Tecnologócias Prisma S.A.
# (http://www.solucionesprisma.com)
#
# This module works with OpenERP 6.0
#

{
    'name': 'Honduras - Accounting',
    'version': '0.1',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Honduras.
====================================================================
    
Agrega una nomenclatura contable para Honduras. También incluye impuestos y la
moneda Lempira. -- Adds accounting chart for Honduras. It also includes taxes
and the Lempira currency.""",
    'author': 'Salvatore Josue Trimarchi Pinto',
    'website': 'http://trimarchi.co.cc',
    'depends': ['base', 'account', 'account_chart'],
    'data': [
        'account_types.xml',
        'account_chart.xml',
        'account_tax.xml',
        'l10n_hn_base.xml',
    ],
    'demo': [],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
