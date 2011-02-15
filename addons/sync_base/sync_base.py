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

from osv import fields,osv,orm

#framework to handle synchronization with multiple app
# we will improve the code and function

class res_partner_sync_base(osv.osv):
    
    _inherit = "res.partner.address"

    def create(self, cr, uid, vals, context=None):
        id = super(res_partner_sync_base, self).create(cr, uid, vals, context=context)   
        return id 

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context = {}
        return super(res_partner_sync_base, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        osv.osv.unlink(self, cr, uid, ids, context=context)
        return True
    
    def sync_create(self, cr, uid, vals, context=None,synchronize=True):
        return True
    
    def sync_modify(self, cr, uid, ids, vals, context=None, synchronize=True):
        return True    
 
    def sync_unlink(self, cr, uid, ids,context=None, synchronize=True):
        return True      

res_partner_sync_base()
