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

import ir
import workflow
import module
import res
import report
import tests

def post_init(cr, registry):
    """Rewrite ICP's to force groups"""
    from openerp import SUPERUSER_ID
    from openerp.addons.base.ir.ir_config_parameter import _default_parameters
    ICP = registry['ir.config_parameter']
    for k, func in _default_parameters.items():
        v = ICP.get_param(cr, SUPERUSER_ID, k)
        _, g = func()
        ICP.set_param(cr, SUPERUSER_ID, k, v, g)
