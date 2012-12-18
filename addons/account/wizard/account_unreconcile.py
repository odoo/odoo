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

from openerp.osv import osv

class account_unreconcile(osv.osv_memory):
    _name = "account.unreconcile"
    _description = "Account Unreconcile"

    def trans_unrec(self, cr, uid, ids, context=None):
        obj_move_line = self.pool.get('account.move.line')
        if context is None:
            context = {}
        if context.get('active_ids', False):
            obj_move_line._remove_move_reconcile(cr, uid, context['active_ids'], context=context)
        return {'type': 'ir.actions.act_window_close'}

account_unreconcile()

class account_unreconcile_reconcile(osv.osv_memory):
    _name = "account.unreconcile.reconcile"
    _description = "Account Unreconcile Reconcile"

    def trans_unrec_reconcile(self, cr, uid, ids, context=None):
        obj_move_reconcile = self.pool.get('account.move.reconcile')
        if context is None:
            context = {}
        rec_ids = context['active_ids']
        if rec_ids:
            obj_move_reconcile.unlink(cr, uid, rec_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}

account_unreconcile_reconcile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
