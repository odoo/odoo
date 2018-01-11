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
from openerp import tools

def rounding(f, r):
	# TODO for trunk: log deprecation warning
	# _logger.warning("Deprecated rounding method, please use tools.float_round to round floats.")
	return tools.float_round(f, precision_rounding=r)

# TODO for trunk: add rounding method parameter to tools.float_round and use this method as hook
def ceiling(f, r):
    if not r:
        return f
    return tools.float_round(f, precision_rounding=r, rounding_method='UP')
