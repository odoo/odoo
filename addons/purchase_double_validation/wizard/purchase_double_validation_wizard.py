# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
from tools import config
import time
from tools.translate import _
import netsvc




class purchase_double_validation_wizard(osv.osv_memory):
    _name = 'purchase.double.validation.wizard'
    
    
    _columns = {
        'limit_amount': fields.float('Limit Amount', required=True),
        
    }
    _defaults = {
        'limit_amount': 100,
        
    }


    def set_limit(self, cr, uid, ids, context=None):
        pur_id = self.pool.get(purchase.order).search(cr, uid, [])
        amount_obj = self.pool.get('purchase.order').browse(cr, uid, pur_id, context)
        amount = amount_obj.amount_total
        return {}
#        limit = limit_obj.limit_amount
#
#        return {
#            'view_type': 'form',
#            "view_mode": 'form',
#            'res_model': 'ir.actions.configuration.wizard',
#            'type': 'ir.actions.act_window',
#            'target': 'new',
#        }

    def action_cancel(self,cr,uid,ids,conect=None):
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'ir.actions.configuration.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
        }
   
purchase_double_validation_wizard()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

