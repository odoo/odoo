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
    'name': 'Just In Time Scheduling with Stock',
    'version': '1.0',
    'category': 'Base',
    'description': """
    If you install this module, it can make sure that not only
    the ship of pick-pack-ship will be created in batch, but
    the pick and the pack also.  (which will dramatically improve performance)

    Will be removed from Saas-6 and will be put in procurement_jit
    over there, where procurement_jit will depend on stock
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/manufacturing',
    'depends': ['procurement_jit', 'stock'],
    'data': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
