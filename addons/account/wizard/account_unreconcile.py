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
from osv import fields, osv

class account_unreconcile(osv.osv_memory):
    _name = "account.unreconcile"
    _description = "Account Unreconcile"

    def trans_unrec(self, cr, uid, ids, context=None):
        obj_move_line = self.pool.get('account.move.line')
        obj_move_reconcile = self.pool.get('account.move.reconcile')
        if context is None:
            context = {}
        recs = obj_move_line.read(cr, uid, data['ids'], ['reconcile_id','reconcile_partial_id'])
        unlink_ids = []
        full_recs = filter(lambda x: x['reconcile_id'], recs)
        rec_ids = [rec['reconcile_id'][0] for rec in full_recs]
        part_recs = filter(lambda x: x['reconcile_partial_id'], recs)
        part_rec_ids = [rec['reconcile_partial_id'][0] for rec in part_recs]
        unlink_ids += rec_ids
        unlink_ids += part_rec_ids

        if len(unlink_ids):
            self.pool.get('account.move.reconcile').unlink(cr, uid, unlink_ids)
        return {}

account_unreconcile()

class account_unreconcile_reconcile(osv.osv_memory):
    _name = "account.unreconcile.reconcile"
    _description = "Account Unreconcile Reconcile"

    def trans_unrec_reconcile(self, cr, uid, ids, context=None):
        obj_move_reconcile = self.pool.get('account.move.reconcile')
        rec_ids = context['active_ids']
        if context is None:
            context = {}
        if len(rec_ids):
            obj_move_reconcile.unlink(cr, uid, rec_ids)
        return {}

account_unreconcile_reconcile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: