# -*- encoding: utf-8 -*-
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
from osv import fields, osv

class account_voucher_unreconcile(osv.osv_memory):
    _name = "account.voucher.unreconcile"
    _description = "Account voucher unreconcile"
    
    def trans_unrec(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        obj_voucher = self.pool.get('account.voucher')
        obj_reconcile = self.pool.get('account.move.reconcile')
        if context.get('active_id'):
            voucher = obj_voucher.browse(cr, uid, context.get('active_id'), context=context)
            recs = []
            for line in voucher.move_ids:
                if line.reconcile_id:
                    recs = [line.reconcile_id.id]
        
            for rec in recs:
                obj_reconcile.unlink(cr, uid, rec)
                
        return {}

account_voucher_unreconcile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: