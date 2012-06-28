# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    
#    Created by Luc De Meyer
#    Copyright (c) 2010 Noviat nv/sa (www.noviat.be). All rights reserved.
# 
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import time
from tools.translate import _

class res_partner(osv.osv):  
    """ add field to indicate default 'Communication Type' on customer invoices """
    _inherit = 'res.partner'
    
    def _get_comm_type(self, cr, uid, context=None):
        res = self.pool.get('account.invoice')._get_reference_type(cr, uid,context=context)
        return res
    
    _columns = {
        'out_inv_comm_type': fields.selection(_get_comm_type, 'Communication Type', change_default=True,
            help='Select Default Communication Type for Outgoing Invoices.' ),
        'out_inv_comm_algorithm': fields.selection([
            ('random','Random'),
            ('date','Date'),
            ('partner_ref','Customer Reference'),
            ], 'Communication Algorithm',
            help='Select Algorithm to generate the Structured Communication on Outgoing Invoices.' ),
    }

    _default = {
        'out_inv_comm_type': 'none',
    }
res_partner()    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
