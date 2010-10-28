# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2010 Soluciones Tecnologócias Prisma S.A. All Rights Reserved.
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
# This module provides a minimal Guatemalan chart of accounts for building upon further
# Open ERP's default currency and accounts are remapped to this chart
#
# This module is based on the UK minimal chart of accounts:
# Copyright (c) 2004-2009 Seath Solutions Ltd. All Rights Reserved.
# Geoff Gardiner, Seath Solutions Ltd (http://www.seathsolutions.com/)
#
# This module works for Open ERP 4.1.0 (and, assumed, onwards).
# This module does not work for Open ERP 4.0.2 and before.
#
# Cash tax accounting can be accommodated with further processing in Open ERP
#
# Status 2.0 - tested on Open ERP 5.0.6
#

{
    'name': 'Guatemala - minimal',
    'version': '2.0',
    'category': 'Localisation/Account Charts',
    'description': """This is the base module to manage a minimal accounting chart for Guatemala in Open ERP.""",
    'author': 'José Rodrigo Fernández Menegazzo',
    'website': 'http://solucionesprisma.com/',
    'depends': ['base', 'base_vat', 'account', 'account_chart'],
    'init_xml': [],
    'update_xml': [
        'account_types.xml',
        'account_chart.xml',
        'account_tax.xml',
        'l10n_gt_wizard.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'certificate': '',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
