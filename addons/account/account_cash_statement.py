# encoding: utf-8
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
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

import time

from osv import osv, fields
from tools.translate import _
import decimal_precision as dp

class account_cashbox_line(osv.osv):

    """ Cash Box Details """

    _name = 'account.cashbox.line'
    _description = 'CashBox Line'
    _rec_name = 'pieces'

    def _sub_total(self, cr, uid, ids, name, arg, context=None):

        """ Calculates Sub total
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = {
                'subtotal_opening' : obj.pieces * obj.number_opening,
                'subtotal_closing' : obj.pieces * obj.number_closing,
            }
        return res

    def on_change_sub_opening(self, cr, uid, ids, pieces, number, *a):
        """ Compute the subtotal for the opening """
        return {'value' : {'subtotal_opening' : (pieces * number) or 0.0 }}

    def on_change_sub_closing(self, cr, uid, ids, pieces, number, *a):
        """ Compute the subtotal for the closing """
        return {'value' : {'subtotal_closing' : (pieces * number) or 0.0 }}

    _columns = {
        'pieces': fields.float('Unit of Currency', digits_compute=dp.get_precision('Account')),
        'number_opening' : fields.integer('Number of Units', help='Opening Unit Numbers'),
        'number_closing' : fields.integer('Number of Units', help='Closing Unit Numbers'),
        'subtotal_opening': fields.function(_sub_total, string='Opening Subtotal', type='float', digits_compute=dp.get_precision('Account'), multi='subtotal'),
        'subtotal_closing': fields.function(_sub_total, string='Closing Subtotal', type='float', digits_compute=dp.get_precision('Account'), multi='subtotal'),
        'bank_statement_id' : fields.many2one('account.bank.statement', ondelete='cascade'),
     }

account_cashbox_line()

class account_cash_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def _update_balances(self, cr, uid, ids, context=None):
        """
            Set starting and ending balances according to pieces count
        """
        res = {}
        for statement in self.browse(cr, uid, ids, context=context):
            if statement.journal_id.type not in ('cash',):
                continue
            start = end = 0
            for line in statement.details_ids:
                start += line.subtotal_opening
                end += line.subtotal_closing
            data = {
                'balance_start': start,
                'balance_end_real': end,
            }
            res[statement.id] = data
            super(account_cash_statement, self).write(cr, uid, [statement.id], data, context=context)
        return res

    def _get_sum_entry_encoding(self, cr, uid, ids, name, arg, context=None):

        """ Find encoding total of statements "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for statement in self.browse(cr, uid, ids, context=context):
            res[statement.id] = sum((line.amount for line in statement.line_ids), 0.0)
        return res

    def _get_company(self, cr, uid, context=None):
        user_pool = self.pool.get('res.users')
        company_pool = self.pool.get('res.company')
        user = user_pool.browse(cr, uid, uid, context=context)
        company_id = user.company_id
        if not company_id:
            company_id = company_pool.search(cr, uid, [])
        return company_id and company_id[0] or False

    def _get_statement_from_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            result[line.statement_id.id] = True
        return result.keys()

    def _compute_difference(self, cr, uid, ids, fieldnames, args, context=None):
        result =  dict.fromkeys(ids, 0.0)

        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = obj.balance_end_real - obj.balance_end

        return result

    def _compute_last_closing_balance(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, 0.0)

        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state == 'draft':
                statement_ids = self.search(cr, uid,
                    [('journal_id', '=', obj.journal_id.id),('state', '=', 'confirm')],
                    order='create_date desc',
                    limit=1,
                    context=context
                )

                if not statement_ids:
                    continue
                else:
                    st = self.browse(cr, uid, statement_ids[0], context=context)
                    result[obj.id] = st.balance_end_real

        return result

    def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
        result = super(account_cash_statement, self).onchange_journal_id(cr, uid, ids, journal_id)

        if not journal_id:
            return result

        statement_ids = self.search(cr, uid,
                [('journal_id', '=', journal_id),('state', '=', 'confirm')],
                order='create_date desc',
                limit=1,
                context=context
        )

        if not statement_ids:
            return result

        st = self.browse(cr, uid, statement_ids[0], context=context)
        result.setdefault('value', {}).update({'last_closing_balance' : st.balance_end_real})

        return result

    _columns = {
        'total_entry_encoding': fields.function(_get_sum_entry_encoding, string="Total Cash Transactions",
            store = {
                'account.bank.statement': (lambda self, cr, uid, ids, context=None: ids, ['line_ids','move_line_ids'], 10),
                'account.bank.statement.line': (_get_statement_from_line, ['amount'], 10),
            }),
        'closing_date': fields.datetime("Closed On"),
        'details_ids' : fields.one2many('account.cashbox.line', 'bank_statement_id', string='CashBox Lines'),
        'opening_details_ids' : fields.one2many('account.cashbox.line', 'bank_statement_id', string='Opening Cashbox Lines'),
        'closing_details_ids' : fields.one2many('account.cashbox.line', 'bank_statement_id', string='Closing Cashbox Lines'),
        'user_id': fields.many2one('res.users', 'Responsible', required=False),
        'difference' : fields.function(_compute_difference, method=True, string="Difference", type="float"),
        'last_closing_balance' : fields.function(_compute_last_closing_balance, method=True, string='Last Closing Balance', type='float'),
    }
    _defaults = {
        'state': 'draft',
        'date': lambda self, cr, uid, context={}: context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")),
        'user_id': lambda self, cr, uid, context=None: uid,
    }

    def create(self, cr, uid, vals, context=None):
        journal = False
        if vals.get('journal_id'):
            journal = self.pool.get('account.journal').browse(cr, uid, vals['journal_id'], context=context)
        if journal and (journal.type == 'cash') and not vals.get('details_ids'):
            vals['details_ids'] = []
            for value in journal.cashbox_line_ids:
                nested_values = {
                    'number_closing' : 0,
                    'number_opening' : 0,
                    'pieces' : value.pieces
                }
                vals['details_ids'].append([0, False, nested_values])

        res_id = super(account_cash_statement, self).create(cr, uid, vals, context=context)
        self._update_balances(cr, uid, [res_id], context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        """
        Update redord(s) comes in {ids}, with new value comes as {vals}
        return True on success, False otherwise

        @param cr: cursor to database
        @param user: id of current user
        @param ids: list of record ids to be update
        @param vals: dict of new values to be set
        @param context: context arguments, like lang, time zone

        @return: True on success, False otherwise
        """

        res = super(account_cash_statement, self).write(cr, uid, ids, vals, context=context)
        self._update_balances(cr, uid, ids, context)
        return res

    def _user_allow(self, cr, uid, statement_id, context=None):
        return True

    def button_open(self, cr, uid, ids, context=None):
        """ Changes statement state to Running.
        @return: True
        """
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}
        statement_pool = self.pool.get('account.bank.statement')
        for statement in statement_pool.browse(cr, uid, ids, context=context):
            vals = {}
            if not self._user_allow(cr, uid, statement.id, context=context):
                raise osv.except_osv(_('Error !'), (_('You do not have rights to open this %s journal !') % (statement.journal_id.name, )))

            if statement.name and statement.name == '/':
                c = {'fiscalyear_id': statement.period_id.fiscalyear_id.id}
                if statement.journal_id.sequence_id:
                    st_number = obj_seq.next_by_id(cr, uid, statement.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.next_by_code(cr, uid, 'account.cash.statement', context=c)
                vals.update({
                    'name': st_number
                })

            vals.update({
                'state': 'open',
            })
            self.write(cr, uid, [statement.id], vals, context=context)
        return True

    def balance_check(self, cr, uid, cash_id, journal_type='bank', context=None):
        if journal_type == 'bank':
            return super(account_cash_statement, self).balance_check(cr, uid, cash_id, journal_type, context)
        if not self._equal_balance(cr, uid, cash_id, context):
            raise osv.except_osv(_('Error !'), _('The closing balance should be equal to compute balance on the cash register !'))
        return True

    def statement_close(self, cr, uid, ids, journal_type='bank', context=None):
        if journal_type == 'bank':
            return super(account_cash_statement, self).statement_close(cr, uid, ids, journal_type, context)
        vals = {
            'state':'confirm',
            'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return self.write(cr, uid, ids, vals, context=context)

    def check_status_condition(self, cr, uid, state, journal_type='bank'):
        if journal_type == 'bank':
            return super(account_cash_statement, self).check_status_condition(cr, uid, state, journal_type)
        return state=='open'

    def button_confirm_cash(self, cr, uid, ids, context=None):
        super(account_cash_statement, self).button_confirm_bank(cr, uid, ids, context=context)
        absl_proxy = self.pool.get('account.bank.statement.line')

        TABLES = (('Profit', 'profit_account_id'), ('Loss', 'loss_account_id'),)

        for obj in self.browse(cr, uid, ids, context=context):
            if obj.difference == 0.0:
                continue

            for item_label, item_account in TALBES:
                if getattr(obj.journal_id, item_account):
                    raise osv.except_osv(_('Error !'), 
                                         _('No %s Account on the Journal %s.') % (item_label, obj.journal_id.name,))

            is_profit = obj.difference < 0.0

            account = getattr(obj.journal_id, TABLES[is_profit][1])

            values = {
                'statement_id' : obj.id,
                'journal_id' : obj.journal_id.id,
                'account_id' : account.id,
                'amount' : obj.difference,
                'name' : 'Exceptional %s' % TABLES[is_profit][0],
            }

            absl_proxy.create(cr, uid, values, context=context)

        return self.write(cr, uid, ids, {'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)

account_cash_statement()

class account_journal(osv.osv):
    _inherit = 'account.journal'

    def _default_cashbox_line_ids(self, cr, uid, context=None):
        # Return a list of coins in Euros.
        result = [
            dict(pieces=value) for value in [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
        ]
        return result

    _columns = {
        'cashbox_line_ids' : fields.one2many('account.journal.cashbox.line', 'journal_id', 'CashBox'),
    }

    _defaults = {
        'cashbox_line_ids' : _default_cashbox_line_ids,
    }

account_journal()

class account_journal_cashbox_line(osv.osv):
    _name = 'account.journal.cashbox.line'
    _rec_name = 'pieces'
    _columns = {
        'pieces': fields.float('Values', digits_compute=dp.get_precision('Account')),
        'journal_id' : fields.many2one('account.journal', 'Journal', required=True, select=1),
    }

    _order = 'pieces asc'

account_journal_cashbox_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
