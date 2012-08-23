# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2009-2010 Soluciones Tecnologócias Prisma S.A. All Rights Reserved.
# José Rodrigo Fernández Menegazzo, Soluciones Tecnologócias Prisma S.A.
# (http://www.solucionesprisma.com)
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
# This module provides a minimal Guatemalan chart of accounts that can be use
# to build upon a more complex one.  It also includes a chart of taxes and
# the Quetzal currency.
#
# This module is based on the UK minimal chart of accounts:
# Copyright (c) 2004-2009 Seath Solutions Ltd. All Rights Reserved.
# Geoff Gardiner, Seath Solutions Ltd (http://www.seathsolutions.com/)
#
# This module works with OpenERP 6.0
#

{
    'name': 'Guatemala - Accounting',
    'version': '3.0',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Guatemala.
=====================================================================

Agrega una nomenclatura contable para Guatemala. También icluye impuestos y
la moneda del Quetzal. -- Adds accounting chart for Guatemala. It also includes
taxes and the Quetzal currency.""",
    'author': 'José Rodrigo Fernández Menegazzo',
    'website': 'http://solucionesprisma.com/',
    'depends': ['base', 'account', 'account_chart'],
    'data': [
        'account_types.xml',
        'account_chart.xml',
        'account_tax.xml',
        'l10n_gt_base.xml',
    ],
    'demo': [],
    'installable': True,
    'certificate': '00815146661827601309',
    'images': ['images/config_chart_l10n_gt.jpeg','images/l10n_gt_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
