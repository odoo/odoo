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
from tools.translate import _

class account_fiscalyear_close(osv.osv_memory):
    """
    Closes Account Fiscalyear and Generate Opening entries for New Fiscalyear
    """
    _name = "account.fiscalyear.close"
    _description = "Fiscalyear Close"
    _columns = {
       'fy_id': fields.many2one('account.fiscalyear', \
                                 'Fiscal Year to close', required=True, help="Select a Fiscal year to close"),
       'fy2_id': fields.many2one('account.fiscalyear', \
                                 'New Fiscal Year', required=True),
       'journal_id': fields.many2one('account.journal', 'Opening Entries Journal', domain="[('type','=','situation')]", required=True, help='The best practice here is to use a journal dedicated to contain the opening entries of all fiscal years. Note that you should define it with default debit/credit accounts, of type \'situation\' and with a centralized counterpart.'),
       'period_id': fields.many2one('account.period', 'Opening Entries Period', required=True),
       'report_name': fields.char('Name of new entries',size=64, required=True, help="Give name of the new entries"),
    }
    _defaults = {
        'report_name': _('End of Fiscal Year Entry'),
    }

    def data_save(self, cr, uid, ids, context=None):
        """
        This function close account fiscalyear and create entries in new fiscalyear
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Account fiscalyear close state’s IDs

        """
        obj_acc_period = self.pool.get('account.period')
        obj_acc_fiscalyear = self.pool.get('account.fiscalyear')
        obj_acc_journal = self.pool.get('account.journal')
        obj_acc_move_line = self.pool.get('account.move.line')
        obj_acc_account = self.pool.get('account.account')
        obj_acc_journal_period = self.pool.get('account.journal.period')

        data = self.browse(cr, uid, ids, context=context)

        if context is None:
            context = {}
        fy_id = data[0].fy_id.id

        cr.execute("SELECT id FROM account_period WHERE date_stop < (SELECT date_start FROM account_fiscalyear WHERE id = %s)", (str(data[0].fy2_id.id),))
        fy_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))
        cr.execute("SELECT id FROM account_period WHERE date_start > (SELECT date_stop FROM account_fiscalyear WHERE id = %s)", (str(fy_id),))
        fy2_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))

        period = obj_acc_period.browse(cr, uid, data[0].period_id.id, context=context)
        new_fyear = obj_acc_fiscalyear.browse(cr, uid, data[0].fy2_id.id, context=context)
        old_fyear = obj_acc_fiscalyear.browse(cr, uid, fy_id, context=context)

        new_journal = data[0].journal_id.id
        new_journal = obj_acc_journal.browse(cr, uid, new_journal, context=context)

        if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
            raise osv.except_osv(_('UserError'),
                    _('The journal must have default credit and debit account'))
        if (not new_journal.centralisation) or new_journal.entry_posted:
            raise osv.except_osv(_('UserError'),
                    _('The journal must have centralised counterpart without the Skipping draft state option checked!'))

        move_ids = obj_acc_move_line.search(cr, uid, [
            ('journal_id', '=', new_journal.id), ('period_id.fiscalyear_id', '=', new_fyear.id)])

        if move_ids:
            obj_acc_move_line._remove_move_reconcile(cr, uid, move_ids, context=context)
            obj_acc_move_line.unlink(cr, uid, move_ids, context=context)

        cr.execute("SELECT id FROM account_fiscalyear WHERE date_stop < %s", (str(new_fyear.date_start),))
        result = cr.dictfetchall()
        fy_ids = ','.join([str(x['id']) for x in result])
        query_line = obj_acc_move_line._query_get(cr, uid,
                obj='account_move_line', context={'fiscalyear': fy_ids})
        cr.execute('select id from account_account WHERE active AND company_id = %s', (old_fyear.company_id.id,))
        ids = map(lambda x: x[0], cr.fetchall())
        for account in obj_acc_account.browse(cr, uid, ids,
            context={'fiscalyear': fy_id}):
            accnt_type_data = account.user_type
            if not accnt_type_data:
                continue
            if accnt_type_data.close_method=='none' or account.type == 'view':
                continue
            if accnt_type_data.close_method=='balance':
                balance_in_currency = 0.0
                if account.currency_id:
                    cr.execute('SELECT sum(amount_currency) as balance_in_currency FROM account_move_line ' \
                            'WHERE account_id = %s ' \
                                'AND ' + query_line + ' ' \
                                'AND currency_id = %s', (account.id, account.currency_id.id)) 
                    balance_in_currency = cr.dictfetchone()['balance_in_currency']

                if abs(account.balance)>0.0001:
                    obj_acc_move_line.create(cr, uid, {
                        'debit': account.balance>0 and account.balance,
                        'credit': account.balance<0 and -account.balance,
                        'name': data[0].report_name,
                        'date': period.date_start,
                        'journal_id': new_journal.id,
                        'period_id': period.id,
                        'account_id': account.id,
                        'currency_id': account.currency_id and account.currency_id.id or False,
                        'amount_currency': balance_in_currency,
                    }, {'journal_id': new_journal.id, 'period_id':period.id})
            if accnt_type_data.close_method == 'unreconciled':
                offset = 0
                limit = 100
                while True:
                    cr.execute('SELECT id, name, quantity, debit, credit, account_id, ref, ' \
                                'amount_currency, currency_id, blocked, partner_id, ' \
                                'date_maturity, date_created ' \
                            'FROM account_move_line ' \
                            'WHERE account_id = %s ' \
                                'AND ' + query_line + ' ' \
                                'AND reconcile_id is NULL ' \
                            'ORDER BY id ' \
                            'LIMIT %s OFFSET %s', (account.id, limit, offset))
                    result = cr.dictfetchall()
                    if not result:
                        break
                    for move in result:
                        move.pop('id')
                        move.update({
                            'date': period.date_start,
                            'journal_id': new_journal.id,
                            'period_id': period.id,
                        })
                        obj_acc_move_line.create(cr, uid, move, {
                            'journal_id': new_journal.id,
                            'period_id': period.id,
                            })
                    offset += limit

                #We have also to consider all move_lines that were reconciled
                #on another fiscal year, and report them too
                offset = 0
                limit = 100
                while True:
                    cr.execute('SELECT  DISTINCT b.id, b.name, b.quantity, b.debit, b.credit, b.account_id, b.ref, ' \
                                'b.amount_currency, b.currency_id, b.blocked, b.partner_id, ' \
                                'b.date_maturity, b.date_created ' \
                            'FROM account_move_line a, account_move_line b ' \
                            'WHERE b.account_id = %s ' \
                                'AND b.reconcile_id is NOT NULL ' \
                                'AND a.reconcile_id = b.reconcile_id ' \
                                'AND b.period_id IN ('+fy_period_set+') ' \
                                'AND a.period_id IN ('+fy2_period_set+') ' \
                            'ORDER BY id ' \
                            'LIMIT %s OFFSET %s', (account.id, limit, offset))
                    result = cr.dictfetchall()
                    if not result:
                        break
                    for move in result:
                        move.pop('id')
                        move.update({
                            'date': period.date_start,
                            'journal_id': new_journal.id,
                            'period_id': period.id,
                        })
                        obj_acc_move_line.create(cr, uid, move, {
                            'journal_id': new_journal.id,
                            'period_id': period.id,
                            })
                    offset += limit
            if accnt_type_data.close_method=='detail':
                offset = 0
                limit = 100
                while True:
                    cr.execute('SELECT id, name, quantity, debit, credit, account_id, ref, ' \
                                'amount_currency, currency_id, blocked, partner_id, ' \
                                'date_maturity, date_created ' \
                            'FROM account_move_line ' \
                            'WHERE account_id = %s ' \
                                'AND ' + query_line + ' ' \
                            'ORDER BY id ' \
                            'LIMIT %s OFFSET %s', (account.id, limit, offset))

                    result = cr.dictfetchall()
                    if not result:
                        break
                    for move in result:
                        move.pop('id')
                        move.update({
                            'date': period.date_start,
                            'journal_id': new_journal.id,
                            'period_id': period.id,
                        })
                        obj_acc_move_line.create(cr, uid, move)
                    offset += limit
        ids = obj_acc_move_line.search(cr, uid, [('journal_id','=',new_journal.id),
            ('period_id.fiscalyear_id','=',new_fyear.id)])
        context['fy_closing'] = True

        if ids:
            obj_acc_move_line.reconcile(cr, uid, ids, context=context)
        new_period = data[0].period_id.id
        ids = obj_acc_journal_period.search(cr, uid, [('journal_id','=',new_journal.id),('period_id','=',new_period)])
        if not ids:
            ids = [obj_acc_journal_period.create(cr, uid, {
                   'name': (new_journal.name or '')+':'+(period.code or ''),
                   'journal_id': new_journal.id,
                   'period_id': period.id
               })]
        cr.execute('UPDATE account_fiscalyear ' \
                    'SET end_journal_period_id = %s ' \
                    'WHERE id = %s', (ids[0], old_fyear.id))
        return {'type': 'ir.actions.act_window_close'}

account_fiscalyear_close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
