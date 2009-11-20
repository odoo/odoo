# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'category': 'Generic Modules/Production',
    'description': """
    This module allows Just In Time computation of all procurement.

    If you install this module, you will not have to run the schedulers anymore.
    Each document is computed in real time. Note that this module can slow down your
    system a little bit.

    It may also increase your stock size because products are reserved as soon
    as possible. In that case, you can not use priorities any more on the different
    picking.
    """,
    'author': 'Tiny',
    'depends': ['mrp', 'sale'],
    'update_xml': ['mrp_jit.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0086634760061',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
