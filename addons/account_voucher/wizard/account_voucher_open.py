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
from osv import osv, fields
from tools.translate import _

_types = {
        'pay_voucher':'Cash Payment Voucher',
        'bank_pay_voucher':'Bank Payment Voucher',
        'rec_voucher':'Cash Receipt Voucher',
        'bank_rec_voucher':'Bank Receipt Voucher',
        'cont_voucher':'Contra Voucher',
        'journal_sale_vou':'Journal Sale Voucher',
        'journal_pur_voucher':'Journal Purchase Voucher'
        }
_states = {
        'draft':'Draft',
        'proforma':'Pro-forma',
        'posted':'Posted',
        'cancel':'Cancel'
        }

class account_open_voucher(osv.osv_memory):
    _name = "account.open.voucher"
    _description = "Account Open Voucher"

    _columns = {
        'type': fields.selection([('pay_voucher','Cash Payment Voucher'),
                             ('bank_pay_voucher','Bank Payment Voucher'),
                             ('rec_voucher','Cash Receipt Voucher'),
                             ('bank_rec_voucher','Bank Receipt Voucher'),
                             ('cont_voucher','Contra Voucher'),
                             ('journal_sale_vou','Journal Sale Voucher'),
                             ('journal_pur_voucher','Journal Purchase Voucher')],'Voucher Type', required=True),
        'state': fields.selection([('draft','Draft'),
                                   ('proforma','Pro-forma'),
                                   ('posted','Posted'),
                                   ('cancel','Cancel')], 'State', required=True),
        'period_ids': fields.many2many('account.period', 'voucher_period_rel', 'voucher_id', 'period_id', 'Periods'),
        }

    def action_open_window(self, cr, uid, ids, context=None):
        obj_period = self.pool.get('account.period')
        obj_fyear = self.pool.get('account.fiscalyear')
        periods = []
        if context is None:
            context = {}

        form = self.read(cr, uid, ids, [])[0]
        if not form['period_ids']:
            year = obj_fyear.find(cr, uid)
            periods = obj_period.search(cr, uid, [('fiscalyear_id','=',year)])
        else:
            periods = form['period_ids']
        return {
            'domain': "[('type','=','%s'), ('state','=','%s'), ('period_id','in',%s)]" % (form['type'], form['state'], periods),
            'name': "%s - %s" % (_types[form['type']], _states[form['state']]),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.voucher',
            'view_id': False,
            'context': "{'type':'%s', 'state':'%s', 'period_id':%s}" % (form['type'], form['state'], periods),
            'type': 'ir.actions.act_window',
            'nodestroy': True
        }

account_open_voucher()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: