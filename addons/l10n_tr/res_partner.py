# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2013-2014 7Gates Interactive Technologies 
#                           <http://www.7gates.co>
#                 @author Erdem Uney
#   
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

class res_partner(osv.osv):
    
    _inherit = "res.partner"
    
    _columns = {
        'vat_dept': fields.char('Tax Department', size=32, help="Tax Identification Department."),
    }
    
    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + ['vat_dept']