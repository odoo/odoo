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

from osv import fields, osv
from tools.translate import _

class account_move_line_reconcile(osv.osv_memory):
    """
    Account move line reconcile wizard, it checks for the write off the reconcile entry or directly reconcile.
    """
    _name = 'account.move.line.reconcile'
    _description = 'Account move line reconcile'
    _columns = {
        'trans_nbr': fields.integer('# of Transaction', readonly=True),
        'credit': fields.float('Credit amount', readonly=True),
        'debit': fields.float('Debit amount', readonly=True),
        'writeoff': fields.float('Write-Off amount', readonly=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(account_move_line_reconcile, self).default_get(cr, uid, fields, context=context)
        data = self.trans_rec_get(cr, uid, context['active_ids'], context)
        if 'trans_nbr' in fields:
            res.update({'trans_nbr':data['trans_nbr']})
        if 'credit' in fields:
            res.update({'credit':data['credit']})
        if 'debit' in fields:
            res.update({'debit':data['debit']})
        if 'writeoff' in fields:
            res.update({'writeoff':data['writeoff']})
        return res

    def trans_rec_get(self, cr, uid, ids, context=None):
        account_move_line_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}
        credit = debit = 0
        account_id = False
        count = 0
        for line in account_move_line_obj.browse(cr, uid, context['active_ids'], context=context):
            if not line.reconcile_id and not line.reconcile_id.id:
                count += 1
                credit += line.credit
                debit += line.debit
                account_id = line.account_id.id
        return {'trans_nbr': count, 'account_id': account_id, 'credit': credit, 'debit': debit, 'writeoff': debit - credit}

    def trans_rec_addendum_writeoff(self, cr, uid, ids, context=None):
        return self.pool.get('account.move.line.reconcile.writeoff').trans_rec_addendum(cr, uid, ids, context)

    def trans_rec_reconcile_partial_reconcile(self, cr, uid, ids, context=None):
        return self.pool.get('account.move.line.reconcile.writeoff').trans_rec_reconcile_partial(cr, uid, ids, context)

    def trans_rec_reconcile_full(self, cr, uid, ids, context=None):
        account_move_line_obj = self.pool.get('account.move.line')
        period_obj = self.pool.get('account.period')
        date = False
        period_id = False
        journal_id= False
        account_id = False

        if context is None:
            context = {}

        date = time.strftime('%Y-%m-%d')
        ids = period_obj.find(cr, uid, dt=date, context=context)
        if ids:
            period_id = ids[0]
        #stop the reconciliation process by partner (manual reconciliation) only if there is nothing more to reconcile for this partner
        if 'active_ids' in context and context['active_ids']:
            tmp_ml_id = account_move_line_obj.browse(cr, uid, context['active_ids'], context)[0]
            partner_id = tmp_ml_id.partner_id and tmp_ml_id.partner_id.id or False
            debit_ml_ids = account_move_line_obj.search(cr, uid, [('partner_id', '=', partner_id), ('account_id.reconcile', '=', True), ('reconcile_id', '=', False), ('debit', '>', 0)], context=context)
            credit_ml_ids = account_move_line_obj.search(cr, uid, [('partner_id', '=', partner_id), ('account_id.reconcile', '=', True), ('reconcile_id', '=', False), ('credit', '>', 0)], context=context)
            for ml_id in context['active_ids']:
                if ml_id in debit_ml_ids:
                    debit_ml_ids.remove(ml_id)
                if ml_id in credit_ml_ids:
                    credit_ml_ids.remove(ml_id)
            if not debit_ml_ids and credit_ml_ids:
                context.update({'stop_reconcile': True})
        account_move_line_obj.reconcile(cr, uid, context['active_ids'], 'manual', account_id,
                                        period_id, journal_id, context=context)
        return {'type': 'ir.actions.act_window_close'}

account_move_line_reconcile()

class account_move_line_reconcile_writeoff(osv.osv_memory):
    """
    It opens the write off wizard form, in that user can define the journal, account, analytic account for reconcile
    """
    _name = 'account.move.line.reconcile.writeoff'
    _description = 'Account move line reconcile'
    _columns = {
        'journal_id': fields.many2one('account.journal','Write-Off Journal', required=True),
        'writeoff_acc_id': fields.many2one('account.account','Write-Off account', required=True),
        'date_p': fields.date('Date'),
        'comment': fields.char('Comment', size= 64, required=True),
        'analytic_id': fields.many2one('account.analytic.account', 'Analytic Account', domain=[('parent_id', '!=', False)]),
    }
    _defaults = {
        'date_p': lambda *a: time.strftime('%Y-%m-%d'),
        'comment': 'Write-off',
    }

    def trans_rec_addendum(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','account_move_line_reconcile_writeoff')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
            'name': _('Reconcile Writeoff'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.line.reconcile.writeoff',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def trans_rec_reconcile_partial(self, cr, uid, ids, context=None):
        account_move_line_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}
        account_move_line_obj.reconcile_partial(cr, uid, context['active_ids'], 'manual', context=context)
        return {'type': 'ir.actions.act_window_close'}

    def trans_rec_reconcile(self, cr, uid, ids, context=None):
        account_move_line_obj = self.pool.get('account.move.line')
        period_obj = self.pool.get('account.period')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids,context=context)[0]
        account_id = data['writeoff_acc_id']
        context['date_p'] = data['date_p']
        journal_id = data['journal_id']
        context['comment'] = data['comment']
        if data['analytic_id']:
            context['analytic_id'] = data['analytic_id']
        if context['date_p']:
            date = context['date_p']

        ids = period_obj.find(cr, uid, dt=date, context=context)
        if ids:
            period_id = ids[0]

        context.update({'stop_reconcile': True})
        account_move_line_obj.reconcile(cr, uid, context['active_ids'], 'manual', account_id,
                period_id, journal_id, context=context)
        return {'type': 'ir.actions.act_window_close'}

account_move_line_reconcile_writeoff()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: