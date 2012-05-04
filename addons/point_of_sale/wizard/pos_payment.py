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

import time

from osv import osv, fields
from tools.translate import _
import pos_box_entries
import netsvc

class account_journal(osv.osv):
    _inherit = 'account.journal'

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}

        session_id = context.get('pos_session_id', False) or False

        if session_id:
            session = self.pool.get('pos.session').browse(cr, uid, session_id, context=context)

            if session:
                journal_ids = [journal.id for journal in session.config_id.journal_ids]
                args += [('id', 'in', journal_ids)]

        return super(account_journal, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

class pos_make_payment(osv.osv_memory):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Payment'
    def check(self, cr, uid, ids, context=None):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        context = context or {}
        order_obj = self.pool.get('pos.order')
        obj_partner = self.pool.get('res.partner')
        active_id = context and context.get('active_id', False)

        order = order_obj.browse(cr, uid, active_id, context=context)
        amount = order.amount_total - order.amount_paid
        data = self.read(cr, uid, ids, context=context)[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        #data['journal'] = data['journal'][0]

        if amount != 0.0:
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        if order_obj.test_paid(cr, uid, [active_id]):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'pos.order', active_id, 'paid', cr)
            return self.print_report(cr, uid, ids, context=context)

        return self.launch_payment(cr, uid, ids, context=context)

    def launch_payment(self, cr, uid, ids, context=None):
        return {
            'name': _('Paiement'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.make.payment',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
        }

    def print_report(self, cr, uid, ids, context=None):
        active_id = context.get('active_id', [])
        datas = {'ids' : [active_id]}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.receipt',
            'datas': datas,
        }

    def _default_journal(self, cr, uid, context=None):
        res = pos_box_entries.get_journal(self, cr, uid, context=context)
        return len(res)>1 and res[1][0] or False

    def _default_amount(self, cr, uid, context=None):
        order_obj = self.pool.get('pos.order')
        active_id = context and context.get('active_id', False)
        if active_id:
            order = order_obj.browse(cr, uid, active_id, context=context)
            return order.amount_total - order.amount_paid
        return False

    _columns = {
        #'journal': fields.selection(pos_box_entries.get_journal, "Payment Mode", required=True),
        'journal_id' : fields.many2one('account.journal', 'Payment Mode', required=True),
        'amount': fields.float('Amount', digits=(16,2), required= True),
        'payment_name': fields.char('Payment Reference', size=32),
        'payment_date': fields.date('Payment Date', required=True),
    }
    _defaults = {
        'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'amount': _default_amount,
        #'journal': _default_journal
    }

pos_make_payment()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
