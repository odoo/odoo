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
    'name': 'MRP JIT',
    'version': '1.0',
    'category': 'Manufacturing',
    'complexity': "easy",
    'description': """
This module allows Just In Time computation of procurement orders.
==================================================================

If you install this module, you will not have to run the regular procurement
scheduler anymore (but you still need to run the minimum order point rule
scheduler, or for example let it run daily.)
All procurement orders will be processed immediately, which could in some
cases entail a small performance impact.

It may also increase your stock size because products are reserved as soon
as possible and the scheduler time range is not taken into account anymore.
In that case, you can not use priorities any more on the different picking.

    """,
    'author': 'OpenERP SA',
    'depends': ['procurement'],
    'update_xml': ['mrp_jit.xml'],
    'demo_xml': [],
    'test': ['test/mrp_jit.yml'],
    'installable': True,
    'active': False,
    'certificate': '0086634760061',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
