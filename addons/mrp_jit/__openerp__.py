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
    'category': 'Generic Modules/Production',
    'description': """
    This module allows Just In Time computation of procurement orders.

    If you install this module, you will not have to run the procurement scheduler
    manually anymore, or wait for it to execute.
    Each procurement order (resulting from a sale order, for instance) will be computed 
    when confirmed, without waiting for the procurement scheduler to run.
    
    Warning: this does not take into account minimum stock rules (order points), which still 
    require to run the appropriate scheduler, or wait for it to run nightly.
     
    Note that the procurement computation can be resource-intensive, so you may 
    want to be careful with this, depending on your mrp configuration and system 
    usage.
    It may also increase your stock size because products are reserved as soon
    as possible. In that case, you can not use priorities any more.
    
    
    """,
    'author': 'Tiny',
    'depends': ['mrp_procurement', 'sale'],
    'update_xml': ['mrp_jit.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0086634760061',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
