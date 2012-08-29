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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

import logging
import pooler
from osv import fields, osv
import decimal_precision as dp
from tools.translate import _
from tools.float_utils import float_round

_logger = logging.getLogger(__name__)

def check_cycle(self, cr, uid, ids, context=None):
    """ climbs the ``self._table.parent_id`` chains for 100 levels or
    until it can't find any more parent(s)

    Returns true if it runs out of parents (no cycle), false if
    it can recurse 100 times without ending all chains
    """
    level = 100
    while len(ids):
        cr.execute('SELECT DISTINCT parent_id '\
                    'FROM '+self._table+' '\
                    'WHERE id IN %s '\
                    'AND parent_id IS NOT NULL',(tuple(ids),))
        ids = map(itemgetter(0), cr.fetchall())
        if not level:
            return False
        level -= 1
    return True

class account_payment_term(osv.osv):
    _name = "account.payment.term"
    _description = "Payment Term"
    _columns = {
        'name': fields.char('Payment Term', size=64, translate=True, required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the payment term without removing it."),
        'note': fields.text('Description', translate=True),
        'line_ids': fields.one2many('account.payment.term.line', 'payment_id', 'Terms'),
    }
    _defaults = {
        'active': 1,
    }
    _order = "name"

    def compute(self, cr, uid, id, value, date_ref=False, context=None):
        if not date_ref:
            date_ref = datetime.now().strftime('%Y-%m-%d')
        pt = self.browse(cr, uid, id, context=context)
        amount = value
        result = []
        obj_precision = self.pool.get('decimal.precision')
        for line in pt.line_ids:
            prec = obj_precision.precision_get(cr, uid, 'Account')
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'procent':
                amt = round(value * line.value_amount, prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1,months=1) #Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                result.append( (next_date.strftime('%Y-%m-%d'), amt) )
                amount -= amt
        return result

account_payment_term()

class account_payment_term_line(osv.osv):
    _name = "account.payment.term.line"
    _description = "Payment Term Line"
    _columns = {
        'name': fields.char('Line Name', size=32, required=True),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the payment term lines from the lowest sequences to the higher ones"),
        'value': fields.selection([('procent', 'Percent'),
                                   ('balance', 'Balance'),
                                   ('fixed', 'Fixed Amount')], 'Valuation',
                                   required=True, help="""Select here the kind of valuation related to this payment term line. Note that you should have your last line with the type 'Balance' to ensure that the whole amount will be treated."""),

        'value_amount': fields.float('Amount To Pay', digits_compute=dp.get_precision('Payment Term'), help="For percent enter a ratio between 0-1."),
        'days': fields.integer('Number of Days', required=True, help="Number of days to add before computation of the day of month." \
            "If Date=15/01, Number of Days=22, Day of Month=-1, then the due date is 28/02."),
        'days2': fields.integer('Day of the Month', required=True, help="Day of the month, set -1 for the last day of the current month. If it's positive, it gives the day of the next month. Set 0 for net days (otherwise it's based on the beginning of the month)."),
        'payment_id': fields.many2one('account.payment.term', 'Payment Term', required=True, select=True),
    }
    _defaults = {
        'value': 'balance',
        'sequence': 5,
        'days2': 0,
    }
    _order = "sequence"

    def _check_percent(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if obj.value == 'procent' and ( obj.value_amount < 0.0 or obj.value_amount > 1.0):
            return False
        return True

    _constraints = [
        (_check_percent, 'Percentages for Payment Term Line must be between 0 and 1, Example: 0.02 for 2%.', ['value_amount']),
    ]

account_payment_term_line()

class account_account_type(osv.osv):
    _name = "account.account.type"
    _description = "Account Type"

    def _get_current_report_type(self, cr, uid, ids, name, arg, context=None):
        obj_data = self.pool.get('ir.model.data')
        obj_financial_report = self.pool.get('account.financial.report')
        res = {}
        financial_report_ref = {
            'asset': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_assets0')[1], context=context),
            'liability': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_liability0')[1], context=context),
            'income': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_income0')[1], context=context),
            'expense': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_expense0')[1], context=context),
        }
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = 'none'
            for key, financial_report in financial_report_ref.items():
                list_ids = [x.id for x in financial_report.account_type_ids]
                if record.id in list_ids:
                    res[record.id] = key
        return res

    def _save_report_type(self, cr, uid, account_type_id, field_name, field_value, arg, context=None):
        obj_data = self.pool.get('ir.model.data')
        obj_financial_report = self.pool.get('account.financial.report')
        #unlink if it exists somewhere in the financial reports related to BS or PL
        financial_report_ref = {
            'asset': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_assets0')[1], context=context),
            'liability': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_liability0')[1], context=context),
            'income': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_income0')[1], context=context),
            'expense': obj_financial_report.browse(cr, uid, obj_data.get_object_reference(cr, uid, 'account','account_financial_report_expense0')[1], context=context),
        }
        for key, financial_report in financial_report_ref.items():
            list_ids = [x.id for x in financial_report.account_type_ids]
            if account_type_id in list_ids:
                obj_financial_report.write(cr, uid, [financial_report.id], {'account_type_ids': [(3, account_type_id)]})
        #write it in the good place
        if field_value != 'none':
            return obj_financial_report.write(cr, uid, [financial_report_ref[field_value].id], {'account_type_ids': [(4, account_type_id)]})

    _columns = {
        'name': fields.char('Account Type', size=64, required=True, translate=True),
        'code': fields.char('Code', size=32, required=True, select=True),
        'close_method': fields.selection([('none', 'None'), ('balance', 'Balance'), ('detail', 'Detail'), ('unreconciled', 'Unreconciled')], 'Deferral Method', required=True, help="""Set here the method that will be used to generate the end of year journal entries for all the accounts of this type.

 'None' means that nothing will be done.
 'Balance' will generally be used for cash accounts.
 'Detail' will copy each existing journal item of the previous year, even the reconciled ones.
 'Unreconciled' will copy only the journal items that were unreconciled on the first day of the new fiscal year."""),
        'report_type': fields.function(_get_current_report_type, fnct_inv=_save_report_type, type='selection', string='P&L / BS Category',
            selection= [('none','/'),
                        ('income', _('Profit & Loss (Income account)')),
                        ('expense', _('Profit & Loss (Expense account)')),
                        ('asset', _('Balance Sheet (Asset account)')),
                        ('liability', _('Balance Sheet (Liability account)'))], help="This field is used to generate legal reports: profit and loss, balance sheet.", required=True),
        'note': fields.text('Description'),
    }
    _defaults = {
        'close_method': 'none',
        'report_type': 'none',
    }
    _order = "code"

account_account_type()

def _code_get(self, cr, uid, context=None):
    acc_type_obj = self.pool.get('account.account.type')
    ids = acc_type_obj.search(cr, uid, [])
    res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context=context)
    return [(r['code'], r['name']) for r in res]

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------

class account_tax(osv.osv):
    _name = 'account.tax'
account_tax()

class account_account(osv.osv):
    _order = "parent_left"
    _parent_order = "code"
    _name = "account.account"
    _description = "Account"
    _parent_store = True

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if context is None:
            context = {}
        pos = 0

        while pos < len(args):

            if args[pos][0] == 'code' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
                args[pos] = ('code', '=like', str(args[pos][2].replace('%', ''))+'%')
            if args[pos][0] == 'journal_id':
                if not args[pos][2]:
                    del args[pos]
                    continue
                jour = self.pool.get('account.journal').browse(cr, uid, args[pos][2], context=context)
                if (not (jour.account_control_ids or jour.type_control_ids)) or not args[pos][2]:
                    args[pos] = ('type','not in',('consolidation','view'))
                    continue
                ids3 = map(lambda x: x.id, jour.type_control_ids)
                ids1 = super(account_account, self).search(cr, uid, [('user_type', 'in', ids3)])
                ids1 += map(lambda x: x.id, jour.account_control_ids)
                args[pos] = ('id', 'in', ids1)
            pos += 1

        if context and context.has_key('consolidate_children'): #add consolidated children of accounts
            ids = super(account_account, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
            for consolidate_child in self.browse(cr, uid, context['account_id'], context=context).child_consol_ids:
                ids.append(consolidate_child.id)
            return ids

        return super(account_account, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)

    def _get_children_and_consol(self, cr, uid, ids, context=None):
        #this function search for all the children and all consolidated children (recursively) of the given account ids
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)], context=context)
        ids3 = []
        for rec in self.browse(cr, uid, ids2, context=context):
            for child in rec.child_consol_ids:
                ids3.append(child.id)
        if ids3:
            ids3 = self._get_children_and_consol(cr, uid, ids3, context)
        return ids2 + ids3

    def __compute(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        """ compute the balance, debit and/or credit for the provided
        account ids
        Arguments:
        `ids`: account ids
        `field_names`: the fields to compute (a list of any of
                       'balance', 'debit' and 'credit')
        `arg`: unused fields.function stuff
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string
                        (__compute will handle their escaping) as a
                        tuple
        """
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        #get all the necessary accounts
        children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)
        #compute for each account the balance/debit/credit from the move lines
        accounts = {}
        res = {}
        null_result = dict((fn, 0.0) for fn in field_names)
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            _logger.debug('Filters: %s',(filters))
            # IN might not work ideally in case there are too many
            # children_and_consolidated, in that case join on a
            # values() e.g.:
            # SELECT l.account_id as id FROM account_move_line l
            # INNER JOIN (VALUES (id1), (id2), (id3), ...) AS tmp (id)
            # ON l.account_id = tmp.id
            # or make _get_children_and_consol return a query and join on that
            request = ("SELECT l.account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM account_move_line l" \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)
            _logger.debug('Status: %s',(cr.statusmessage))

            for row in cr.dictfetchall():
                accounts[row['id']] = row

            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
            sums = {}
            currency_obj = self.pool.get('res.currency')
            while brs:
                current = brs.pop(0)
#                can_compute = True
#                for child in current.child_id:
#                    if child.id not in sums:
#                        can_compute = False
#                        try:
#                            brs.insert(0, brs.pop(brs.index(child)))
#                        except ValueError:
#                            brs.insert(0, child)
#                if can_compute:
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)

                # as we have to relay on values computed before this is calculated separately than previous fields
                if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
                    adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
                    sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})

            for id in ids:
                res[id] = sums.get(id, null_result)
        else:
            for id in ids:
                res[id] = null_result
        return res

    def _get_company_currency(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for rec in self.browse(cr, uid, ids, context=context):
            result[rec.id] = (rec.company_id.currency_id.id,rec.company_id.currency_id.symbol)
        return result

    def _get_child_ids(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            if record.child_parent_ids:
                result[record.id] = [x.id for x in record.child_parent_ids]
            else:
                result[record.id] = []

            if record.child_consol_ids:
                for acc in record.child_consol_ids:
                    if acc.id not in result[record.id]:
                        result[record.id].append(acc.id)

        return result

    def _get_level(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            #we may not know the level of the parent at the time of computation, so we
            # can't simply do res[account.id] = account.parent_id.level + 1
            level = 0
            parent = account.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            res[account.id] = level
        return res

    def _set_credit_debit(self, cr, uid, account_id, name, value, arg, context=None):
        if context.get('config_invisible', True):
            return True

        account = self.browse(cr, uid, account_id, context=context)
        diff = value - getattr(account,name)
        if not diff:
            return True

        journal_obj = self.pool.get('account.journal')
        jids = journal_obj.search(cr, uid, [('type','=','situation'),('centralisation','=',1),('company_id','=',account.company_id.id)], context=context)
        if not jids:
            raise osv.except_osv(_('Error!'),_("You need an Opening journal with centralisation checked to set the initial balance."))

        period_obj = self.pool.get('account.period')
        pids = period_obj.search(cr, uid, [('special','=',True),('company_id','=',account.company_id.id)], context=context)
        if not pids:
            raise osv.except_osv(_('Error!'),_("There is no opening/closing period defined, please create one to set the initial balance."))

        move_obj = self.pool.get('account.move.line')
        move_id = move_obj.search(cr, uid, [
            ('journal_id','=',jids[0]),
            ('period_id','=',pids[0]),
            ('account_id','=', account_id),
            (name,'>', 0.0),
            ('name','=', _('Opening Balance'))
        ], context=context)
        if move_id:
            move = move_obj.browse(cr, uid, move_id[0], context=context)
            move_obj.write(cr, uid, move_id[0], {
                name: diff+getattr(move,name)
            }, context=context)
        else:
            if diff<0.0:
                raise osv.except_osv(_('Error!'),_("Unable to adapt the initial balance (negative value)."))
            nameinv = (name=='credit' and 'debit') or 'credit'
            move_id = move_obj.create(cr, uid, {
                'name': _('Opening Balance'),
                'account_id': account_id,
                'journal_id': jids[0],
                'period_id': pids[0],
                name: diff,
                nameinv: 0.0
            }, context=context)
        return True

    _columns = {
        'name': fields.char('Name', size=256, required=True, select=True),
        'currency_id': fields.many2one('res.currency', 'Secondary Currency', help="Forces all moves for this account to have this secondary currency."),
        'code': fields.char('Code', size=64, required=True, select=1),
        'type': fields.selection([
            ('view', 'View'),
            ('other', 'Regular'),
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('liquidity','Liquidity'),
            ('consolidation', 'Consolidation'),
            ('closed', 'Closed'),
        ], 'Internal Type', required=True, help="The 'Internal Type' is used for features available on "\
            "different types of accounts: view can not have journal items, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts."),
        'user_type': fields.many2one('account.account.type', 'Account Type', required=True,
            help="Account Type is used for information purpose, to generate "
              "country-specific legal reports, and set the rules to close a fiscal year and generate opening entries."),
        'financial_report_ids': fields.many2many('account.financial.report', 'account_account_financial_report', 'account_id', 'report_line_id', 'Financial Reports'),
        'parent_id': fields.many2one('account.account', 'Parent', ondelete='cascade', domain=[('type','=','view')]),
        'child_parent_ids': fields.one2many('account.account','parent_id','Children'),
        'child_consol_ids': fields.many2many('account.account', 'account_account_consol_rel', 'child_id', 'parent_id', 'Consolidated Children'),
        'child_id': fields.function(_get_child_ids, type='many2many', relation="account.account", string="Child Accounts"),
        'balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Balance', multi='balance'),
        'credit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Credit', multi='balance'),
        'debit': fields.function(__compute, fnct_inv=_set_credit_debit, digits_compute=dp.get_precision('Account'), string='Debit', multi='balance'),
        'foreign_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Foreign Balance', multi='balance',
                                           help="Total amount (in Secondary currency) for transactions held in secondary currency for this account."),
        'adjusted_balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Adjusted Balance', multi='balance',
                                            help="Total amount (in Company currency) for transactions held in secondary currency for this account."),
        'unrealized_gain_loss': fields.function(__compute, digits_compute=dp.get_precision('Account'), string='Unrealized Gain or Loss', multi='balance',
                                                help="Value of Loss or Gain due to changes in exchange rate when doing multi-currency transactions."),
        'reconcile': fields.boolean('Allow Reconciliation', help="Check this box if this account allows reconciliation of journal items."),
        'exchange_rate': fields.related('currency_id', 'rate', type='float', string='Exchange Rate', digits=(12,6)),
        'shortcut': fields.char('Shortcut', size=12),
        'tax_ids': fields.many2many('account.tax', 'account_account_tax_default_rel',
            'account_id', 'tax_id', 'Default Taxes'),
        'note': fields.text('Internal Notes'),
        'company_currency_id': fields.function(_get_company_currency, type='many2one', relation='res.currency', string='Company Currency'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'active': fields.boolean('Active', select=2, help="If the active field is set to False, it will allow you to hide the account without removing it."),

        'parent_left': fields.integer('Parent Left', select=1),
        'parent_right': fields.integer('Parent Right', select=1),
        'currency_mode': fields.selection([('current', 'At Date'), ('average', 'Average Rate')], 'Outgoing Currencies Rate',
            help=
            'This will select how the current currency rate for outgoing transactions is computed. '\
            'In most countries the legal method is "average" but only a few software systems are able to '\
            'manage this. So if you import from another software system you may have to use the rate at date. ' \
            'Incoming transactions always use the rate at date.', \
            required=True),
        'level': fields.function(_get_level, string='Level', method=True, type='integer',
             store={
                    'account.account': (_get_children_and_consol, ['level', 'parent_id'], 10),
                   }),
    }

    _defaults = {
        'type': 'other',
        'reconcile': False,
        'active': True,
        'currency_mode': 'current',
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        obj_self = self.browse(cr, uid, ids[0], context=context)
        p_id = obj_self.parent_id and obj_self.parent_id.id
        if (obj_self in obj_self.child_consol_ids) or (p_id and (p_id is obj_self.id)):
            return False
        while(ids):
            cr.execute('SELECT DISTINCT child_id '\
                       'FROM account_account_consol_rel '\
                       'WHERE parent_id IN %s', (tuple(ids),))
            child_ids = map(itemgetter(0), cr.fetchall())
            c_ids = child_ids
            if (p_id and (p_id in c_ids)) or (obj_self.id in c_ids):
                return False
            while len(c_ids):
                s_ids = self.search(cr, uid, [('parent_id', 'in', c_ids)])
                if p_id and (p_id in s_ids):
                    return False
                c_ids = s_ids
            ids = child_ids
        return True

    def _check_type(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        accounts = self.browse(cr, uid, ids, context=context)
        for account in accounts:
            if account.child_id and account.type not in ('view', 'consolidation'):
                return False
        return True

    def _check_account_type(self, cr, uid, ids, context=None):
        for account in self.browse(cr, uid, ids, context=context):
            if account.type in ('receivable', 'payable') and account.user_type.close_method != 'unreconciled':
                return False
        return True

    _constraints = [
        (_check_recursion, 'Error!\nYou cannot create recursive accounts.', ['parent_id']),
        (_check_type, 'Configuration Error!\nYou cannot define children to an account with internal type different of "View".', ['type']),
        (_check_account_type, 'Configuration Error!\nYou cannot select an account type with a deferral method different of "Unreconciled" for accounts with internal type "Payable/Receivable".', ['user_type','type']),
    ]
    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        args = args[:]
        ids = []
        try:
            if name and str(name).startswith('partner:'):
                part_id = int(name.split(':')[1])
                part = self.pool.get('res.partner').browse(cr, user, part_id, context=context)
                args += [('id', 'in', (part.property_account_payable.id, part.property_account_receivable.id))]
                name = False
            if name and str(name).startswith('type:'):
                type = name.split(':')[1]
                args += [('type', '=', type)]
                name = False
        except:
            pass
        if name:
            ids = self.search(cr, user, [('code', '=like', name+"%")]+args, limit=limit)
            if not ids:
                ids = self.search(cr, user, [('shortcut', '=', name)]+ args, limit=limit)
            if not ids:
                ids = self.search(cr, user, [('name', operator, name)]+ args, limit=limit)
            if not ids and len(name.split()) >= 2:
                #Separating code and name of account for searching
                operand1,operand2 = name.split(' ',1) #name can contain spaces e.g. OpenERP S.A.
                ids = self.search(cr, user, [('code', operator, operand1), ('name', operator, operand2)]+ args, limit=limit)
        else:
            ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
                    ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'code'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code'] + ' ' + name
            res.append((record['id'], name))
        return res

    def copy(self, cr, uid, id, default={}, context=None, done_list=[], local=False):
        account = self.browse(cr, uid, id, context=context)
        new_child_ids = []
        if not default:
            default = {}
        default = default.copy()
        default['code'] = (account['code'] or '') + '(copy)'
        if not local:
            done_list = []
        if account.id in done_list:
            return False
        done_list.append(account.id)
        if account:
            for child in account.child_id:
                child_ids = self.copy(cr, uid, child.id, default, context=context, done_list=done_list, local=True)
                if child_ids:
                    new_child_ids.append(child_ids)
            default['child_parent_ids'] = [(6, 0, new_child_ids)]
        else:
            default['child_parent_ids'] = False
        return super(account_account, self).copy(cr, uid, id, default, context=context)

    def _check_moves(self, cr, uid, ids, method, context=None):
        line_obj = self.pool.get('account.move.line')
        account_ids = self.search(cr, uid, [('id', 'child_of', ids)])

        if line_obj.search(cr, uid, [('account_id', 'in', account_ids)]):
            if method == 'write':
                raise osv.except_osv(_('Error!'), _('You cannot deactivate an account that contains journal items.'))
            elif method == 'unlink':
                raise osv.except_osv(_('Error!'), _('You cannot remove an account that contains journal items.'))
        #Checking whether the account is set as a property to any Partner or not
        value = 'account.account,' + str(ids[0])
        partner_prop_acc = self.pool.get('ir.property').search(cr, uid, [('value_reference','=',value)], context=context)
        if partner_prop_acc:
            raise osv.except_osv(_('Warning!'), _('You cannot remove/deactivate an account which is set on a customer or supplier.'))
        return True

    def _check_allow_type_change(self, cr, uid, ids, new_type, context=None):
        group1 = ['payable', 'receivable', 'other']
        group2 = ['consolidation','view']
        line_obj = self.pool.get('account.move.line')
        for account in self.browse(cr, uid, ids, context=context):
            old_type = account.type
            account_ids = self.search(cr, uid, [('id', 'child_of', [account.id])])
            if line_obj.search(cr, uid, [('account_id', 'in', account_ids)]):
                #Check for 'Closed' type
                if old_type == 'closed' and new_type !='closed':
                    raise osv.except_osv(_('Warning!'), _("You cannot change the type of account from 'Closed' to any other type which contains journal items!"))
                #Check for change From group1 to group2 and vice versa
                if (old_type in group1 and new_type in group2) or (old_type in group2 and new_type in group1):
                    raise osv.except_osv(_('Warning!'), _("You cannot change the type of account from '%s' to '%s' type as it contains journal items!") % (old_type,new_type,))
        return True

    def write(self, cr, uid, ids, vals, context=None):

        if context is None:
            context = {}
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]

        # Dont allow changing the company_id when account_move_line already exist
        if 'company_id' in vals:
            move_lines = self.pool.get('account.move.line').search(cr, uid, [('account_id', 'in', ids)])
            if move_lines:
                # Allow the write if the value is the same
                for i in [i['company_id'][0] for i in self.read(cr,uid,ids,['company_id'])]:
                    if vals['company_id']!=i:
                        raise osv.except_osv(_('Warning!'), _('You cannot change the owner company of an account that already contains journal items.'))
        if 'active' in vals and not vals['active']:
            self._check_moves(cr, uid, ids, "write", context=context)
        if 'type' in vals.keys():
            self._check_allow_type_change(cr, uid, ids, vals['type'], context=context)
        return super(account_account, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        self._check_moves(cr, uid, ids, "unlink", context=context)
        return super(account_account, self).unlink(cr, uid, ids, context=context)

account_account()

class account_journal_view(osv.osv):
    _name = "account.journal.view"
    _description = "Journal View"
    _columns = {
        'name': fields.char('Journal View', size=64, required=True),
        'columns_id': fields.one2many('account.journal.column', 'view_id', 'Columns')
    }
    _order = "name"

account_journal_view()


class account_journal_column(osv.osv):

    def _col_get(self, cr, user, context=None):
        result = []
        cols = self.pool.get('account.move.line')._columns
        for col in cols:
            if col in ('period_id', 'journal_id'):
                continue
            result.append( (col, cols[col].string) )
        result.sort()
        return result

    _name = "account.journal.column"
    _description = "Journal Column"
    _columns = {
        'name': fields.char('Column Name', size=64, required=True),
        'field': fields.selection(_col_get, 'Field Name', required=True, size=32),
        'view_id': fields.many2one('account.journal.view', 'Journal View', select=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order to journal column.", readonly=True),
        'required': fields.boolean('Required'),
        'readonly': fields.boolean('Readonly'),
    }
    _order = "view_id, sequence"

account_journal_column()

class account_journal(osv.osv):
    _name = "account.journal"
    _description = "Journal"
    _columns = {
        'with_last_closing_balance' : fields.boolean('Opening With Last Closing Balance'),
        'name': fields.char('Journal Name', size=64, required=True),
        'code': fields.char('Code', size=5, required=True, help="The code will be displayed on reports."),
        'type': fields.selection([('sale', 'Sale'),('sale_refund','Sale Refund'), ('purchase', 'Purchase'), ('purchase_refund','Purchase Refund'), ('cash', 'Cash'), ('bank', 'Bank and Cheques'), ('general', 'General'), ('situation', 'Opening/Closing Situation')], 'Type', size=32, required=True,
                                 help="Select 'Sale' for customer invoices journals."\
                                 " Select 'Purchase' for supplier invoices journals."\
                                 " Select 'Cash' or 'Bank' for journals that are used in customer or supplier payments."\
                                 " Select 'General' for miscellaneous operations journals."\
                                 " Select 'Opening/Closing Situation' for entries generated for new fiscal years."),
        'type_control_ids': fields.many2many('account.account.type', 'account_journal_type_rel', 'journal_id','type_id', 'Type Controls', domain=[('code','<>','view'), ('code', '<>', 'closed')]),
        'account_control_ids': fields.many2many('account.account', 'account_account_type_rel', 'journal_id','account_id', 'Account', domain=[('type','<>','view'), ('type', '<>', 'closed')]),
        'view_id': fields.many2one('account.journal.view', 'Display Mode', required=True, help="Gives the view used when writing or browsing entries in this journal. The view tells OpenERP which fields should be visible, required or readonly and in which order. You can create your own view for a faster encoding in each journal."),
        'default_credit_account_id': fields.many2one('account.account', 'Default Credit Account', domain="[('type','!=','view')]", help="It acts as a default account for credit amount"),
        'default_debit_account_id': fields.many2one('account.account', 'Default Debit Account', domain="[('type','!=','view')]", help="It acts as a default account for debit amount"),
        'centralisation': fields.boolean('Centralised Counterpart', help="Check this box to determine that each entry of this journal won't create a new counterpart but will share the same counterpart. This is used in fiscal year closing."),
        'update_posted': fields.boolean('Allow Cancelling Entries', help="Check this box if you want to allow the cancellation the entries related to this journal or of the invoice related to this journal"),
        'group_invoice_lines': fields.boolean('Group Invoice Lines', help="If this box is checked, the system will try to group the accounting lines when generating them from invoices."),
        'sequence_id': fields.many2one('ir.sequence', 'Entry Sequence', help="This field contains the information related to the numbering of the journal entries of this journal.", required=True),
        'user_id': fields.many2one('res.users', 'User', help="The user responsible for this journal"),
        'groups_id': fields.many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', 'Groups'),
        'currency': fields.many2one('res.currency', 'Currency', help='The currency used to enter statement'),
        'entry_posted': fields.boolean('Skip \'Draft\' State for Manual Entries', help='Check this box if you don\'t want new journal entries to pass through the \'draft\' state and instead goes directly to the \'posted state\' without any manual validation. \nNote that journal entries that are automatically created by the system are always skipping that state.'),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=1, help="Company related to this journal"),
        'allow_date':fields.boolean('Check Date in Period', help= 'If set to True then do not accept the entry if the entry date is not into the period dates'),

        'profit_account_id' : fields.many2one('account.account', 'Profit Account'),
        'loss_account_id' : fields.many2one('account.account', 'Loss Account'),
        'internal_account_id' : fields.many2one('account.account', 'Internal Transfers Account', select=1),
    }

    _defaults = {
        'with_last_closing_balance' : False,
        'user_id': lambda self, cr, uid, context: uid,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _sql_constraints = [
        ('code_company_uniq', 'unique (code, company_id)', 'The code of the journal must be unique per company !'),
        ('name_company_uniq', 'unique (name, company_id)', 'The name of the journal must be unique per company !'),
    ]

    _order = 'code'

    def _check_currency(self, cr, uid, ids, context=None):
        for journal in self.browse(cr, uid, ids, context=context):
            if journal.currency:
                if journal.default_credit_account_id and not journal.default_credit_account_id.currency_id.id == journal.currency.id:
                    return False
                if journal.default_debit_account_id and not journal.default_debit_account_id.currency_id.id == journal.currency.id:
                    return False
        return True

    _constraints = [
        (_check_currency, 'Configuration error!\nThe currency chosen should be shared by the default accounts too.', ['currency','default_debit_account_id','default_credit_account_id']),
    ]

    def copy(self, cr, uid, id, default={}, context=None, done_list=[], local=False):
        journal = self.browse(cr, uid, id, context=context)
        if not default:
            default = {}
        default = default.copy()
        default['code'] = (journal['code'] or '') + '(copy)'
        default['name'] = (journal['name'] or '') + '(copy)'
        default['sequence_id'] = False
        return super(account_journal, self).copy(cr, uid, id, default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        for journal in self.browse(cr, uid, ids, context=context):
            if 'company_id' in vals and journal.company_id.id != vals['company_id']:
                move_lines = self.pool.get('account.move.line').search(cr, uid, [('journal_id', 'in', ids)])
                if move_lines:
                    raise osv.except_osv(_('Warning!'), _('This journal already contains items, therefore you cannot modify its company field.'))
        return super(account_journal, self).write(cr, uid, ids, vals, context=context)

    def create_sequence(self, cr, uid, vals, context=None):
        """ Create new no_gap entry sequence for every new Joural
        """
        # in account.journal code is actually the prefix of the sequence
        # whereas ir.sequence code is a key to lookup global sequences.
        prefix = vals['code'].upper()

        seq = {
            'name': vals['name'],
            'implementation':'no_gap',
            'prefix': prefix + "/%(year)s/",
            'padding': 4,
            'number_increment': 1
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.pool.get('ir.sequence').create(cr, uid, seq)

    def create(self, cr, uid, vals, context=None):
        if not 'sequence_id' in vals or not vals['sequence_id']:
            # if we have the right to create a journal, we should be able to
            # create it's sequence.
            vals.update({'sequence_id': self.create_sequence(cr, 1, vals, context)})
        return super(account_journal, self).create(cr, uid, vals, context)

    def name_get(self, cr, user, ids, context=None):
        """
        Returns a list of tupples containing id, name.
        result format: {[(id, name), (id, name), ...]}

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param ids: list of ids for which name should be read
        @param context: context arguments, like lang, time zone

        @return: Returns a list of tupples containing id, name
        """
        if not isinstance(ids, list):
            ids = [ids]
        result = self.browse(cr, user, ids, context=context)
        res = []
        for rs in result:
            if rs.currency:
                currency = rs.currency
            else:
                currency = rs.company_id.currency_id
            name = "%s (%s)" % (rs.name, currency.name)
            res += [(rs.id, name)]
        return res

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if context.get('journal_type', False):
            args += [('type','=',context.get('journal_type'))]
        if name:
            ids = self.search(cr, user, [('code', 'ilike', name)]+ args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name', 'ilike', name)]+ args, limit=limit, context=context)#fix it ilike should be replace with operator

        return self.name_get(cr, user, ids, context=context)

    def onchange_type(self, cr, uid, ids, type, currency, context=None):
        obj_data = self.pool.get('ir.model.data')
        user_pool = self.pool.get('res.users')

        type_map = {
            'sale':'account_sp_journal_view',
            'sale_refund':'account_sp_refund_journal_view',
            'purchase':'account_sp_journal_view',
            'purchase_refund':'account_sp_refund_journal_view',
            'cash':'account_journal_bank_view',
            'bank':'account_journal_bank_view',
            'general':'account_journal_view',
            'situation':'account_journal_view'
        }

        res = {}
        view_id = type_map.get(type, 'account_journal_view')
        user = user_pool.browse(cr, uid, uid)
        if type in ('cash', 'bank') and currency and user.company_id.currency_id.id != currency:
            view_id = 'account_journal_bank_view_multi'
        data_id = obj_data.search(cr, uid, [('model','=','account.journal.view'), ('name','=',view_id)])
        data = obj_data.browse(cr, uid, data_id[0], context=context)

        res.update({
            'centralisation':type == 'situation',
            'view_id':data.res_id,
        })
        return {
            'value':res
        }

account_journal()

class account_fiscalyear(osv.osv):
    _name = "account.fiscalyear"
    _description = "Fiscal Year"
    _columns = {
        'name': fields.char('Fiscal Year', size=64, required=True),
        'code': fields.char('Code', size=6, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period_ids': fields.one2many('account.period', 'fiscalyear_id', 'Periods'),
        'state': fields.selection([('draft','Open'), ('done','Closed')], 'Status', readonly=True),
    }
    _defaults = {
        'state': 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _order = "date_start, id"


    def _check_duration(self, cr, uid, ids, context=None):
        obj_fy = self.browse(cr, uid, ids[0], context=context)
        if obj_fy.date_stop < obj_fy.date_start:
            return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe start date of a fiscal year must precede its end date.', ['date_start','date_stop'])
    ]

    def create_period3(self, cr, uid, ids, context=None):
        return self.create_period(cr, uid, ids, context, 3)

    def create_period(self, cr, uid, ids, context=None, interval=1):
        period_obj = self.pool.get('account.period')
        for fy in self.browse(cr, uid, ids, context=context):
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
            period_obj.create(cr, uid, {
                    'name':  "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                    'code': ds.strftime('00/%Y'),
                    'date_start': ds,
                    'date_stop': ds,
                    'special': True,
                    'fiscalyear_id': fy.id,
                })
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)

                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')

                period_obj.create(cr, uid, {
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

    def find(self, cr, uid, dt=None, exception=True, context=None):
        res = self.finds(cr, uid, dt, exception, context=context)
        return res and res[0] or False

    def finds(self, cr, uid, dt=None, exception=True, context=None):
        if context is None: context = {}
        if not dt:
            dt = fields.date.context_today(self,cr,uid,context=context)
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
        if context.get('company_id', False):
            company_id = context['company_id']
        else:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        args.append(('company_id', '=', company_id))
        ids = self.search(cr, uid, args, context=context)
        if not ids:
            if exception:
                raise osv.except_osv(_('Error!'), _('There is no fiscal year defined for this date.\nPlease create one from the configuration of the accounting menu.'))
            else:
                return []
        return ids

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if args is None:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code', 'ilike', name)]+ args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)]+ args, limit=limit)
        return self.name_get(cr, user, ids, context=context)

account_fiscalyear()

class account_period(osv.osv):
    _name = "account.period"
    _description = "Account period"
    _columns = {
        'name': fields.char('Period Name', size=64, required=True),
        'code': fields.char('Code', size=12),
        'special': fields.boolean('Opening/Closing Period', size=12,
            help="These periods can overlap."),
        'date_start': fields.date('Start of Period', required=True, states={'done':[('readonly',True)]}),
        'date_stop': fields.date('End of Period', required=True, states={'done':[('readonly',True)]}),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, states={'done':[('readonly',True)]}, select=True),
        'state': fields.selection([('draft','Open'), ('done','Closed')], 'Status', readonly=True,
                                  help='When monthly periods are created. The state is \'Draft\'. At the end of monthly period it is in \'Done\' state.'),
        'company_id': fields.related('fiscalyear_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True)
    }
    _defaults = {
        'state': 'draft',
    }
    _order = "date_start, special desc"
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
    ]

    def _check_duration(self,cr,uid,ids,context=None):
        obj_period = self.browse(cr, uid, ids[0], context=context)
        if obj_period.date_stop < obj_period.date_start:
            return False
        return True

    def _check_year_limit(self,cr,uid,ids,context=None):
        for obj_period in self.browse(cr, uid, ids, context=context):
            if obj_period.special:
                continue

            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
               obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                return False

            pids = self.search(cr, uid, [('date_stop','>=',obj_period.date_start),('date_start','<=',obj_period.date_stop),('special','=',False),('id','<>',obj_period.id)])
            for period in self.browse(cr, uid, pids):
                if period.fiscalyear_id.company_id.id==obj_period.fiscalyear_id.company_id.id:
                    return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe duration of the Period(s) is/are invalid.', ['date_stop']),
        (_check_year_limit, 'Error!\nThe period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.', ['date_stop'])
    ]

    def next(self, cr, uid, period, step, context=None):
        ids = self.search(cr, uid, [('date_start','>',period.date_start)])
        if len(ids)>=step:
            return ids[step-1]
        return False

    def find(self, cr, uid, dt=None, context=None):
        if context is None: context = {}
        if not dt:
            dt = fields.date.context_today(self,cr,uid,context=context)
#CHECKME: shouldn't we check the state of the period?
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
        if context.get('company_id', False):
            args.append(('company_id', '=', context['company_id']))
        else:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            args.append(('company_id', '=', company_id))
        ids = self.search(cr, uid, args, context=context)
        if not ids:
            raise osv.except_osv(_('Error!'), _('There is no period defined for this date: %s.\nPlease create one.')%dt)
        return ids

    def action_draft(self, cr, uid, ids, *args):
        mode = 'draft'
        cr.execute('update account_journal_period set state=%s where period_id in %s', (mode, tuple(ids),))
        cr.execute('update account_period set state=%s where id in %s', (mode, tuple(ids),))
        return True

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if args is None:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','ilike',name)]+ args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit)
        return self.name_get(cr, user, ids, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'company_id' in vals:
            move_lines = self.pool.get('account.move.line').search(cr, uid, [('period_id', 'in', ids)])
            if move_lines:
                raise osv.except_osv(_('Warning!'), _('This journal already contains items for this period, therefore you cannot modify its company field.'))
        return super(account_period, self).write(cr, uid, ids, vals, context=context)

    def build_ctx_periods(self, cr, uid, period_from_id, period_to_id):
        if period_from_id == period_to_id:
            return [period_from_id]
        period_from = self.browse(cr, uid, period_from_id)
        period_date_start = period_from.date_start
        company1_id = period_from.company_id.id
        period_to = self.browse(cr, uid, period_to_id)
        period_date_stop = period_to.date_stop
        company2_id = period_to.company_id.id
        if company1_id != company2_id:
            raise osv.except_osv(_('Error!'), _('You should choose the periods that belong to the same company.'))
        if period_date_start > period_date_stop:
            raise osv.except_osv(_('Error!'), _('Start period should precede then end period.'))
        #for period from = january, we want to exclude the opening period (but it has same date_from, so we have to check if period_from is special or not to include that clause or not in the search).
        if period_from.special:
            return self.search(cr, uid, [('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('company_id', '=', company1_id)])
        return self.search(cr, uid, [('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('company_id', '=', company1_id), ('special', '=', False)])

account_period()

class account_journal_period(osv.osv):
    _name = "account.journal.period"
    _description = "Journal Period"

    def _icon_get(self, cr, uid, ids, field_name, arg=None, context=None):
        result = {}.fromkeys(ids, 'STOCK_NEW')
        for r in self.read(cr, uid, ids, ['state']):
            result[r['id']] = {
                'draft': 'STOCK_NEW',
                'printed': 'STOCK_PRINT_PREVIEW',
                'done': 'STOCK_DIALOG_AUTHENTICATION',
            }.get(r['state'], 'STOCK_NEW')
        return result

    _columns = {
        'name': fields.char('Journal-Period Name', size=64, required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, ondelete="cascade"),
        'period_id': fields.many2one('account.period', 'Period', required=True, ondelete="cascade"),
        'icon': fields.function(_icon_get, string='Icon', type='char', size=32),
        'active': fields.boolean('Active', required=True, help="If the active field is set to False, it will allow you to hide the journal period without removing it."),
        'state': fields.selection([('draft','Draft'), ('printed','Printed'), ('done','Done')], 'Status', required=True, readonly=True,
                                  help='When journal period is created. The state is \'Draft\'. If a report is printed it comes to \'Printed\' state. When all transactions are done, it comes in \'Done\' state.'),
        'fiscalyear_id': fields.related('period_id', 'fiscalyear_id', string='Fiscal Year', type='many2one', relation='account.fiscalyear'),
        'company_id': fields.related('journal_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True)
    }

    def _check(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            cr.execute('select * from account_move_line where journal_id=%s and period_id=%s limit 1', (obj.journal_id.id, obj.period_id.id))
            res = cr.fetchall()
            if res:
                raise osv.except_osv(_('Error!'), _('You cannot modify/delete a journal with entries for this period.'))
        return True

    def write(self, cr, uid, ids, vals, context=None):
        self._check(cr, uid, ids, context=context)
        return super(account_journal_period, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        period_id = vals.get('period_id',False)
        if period_id:
            period = self.pool.get('account.period').browse(cr, uid, period_id, context=context)
            vals['state']=period.state
        return super(account_journal_period, self).create(cr, uid, vals, context)

    def unlink(self, cr, uid, ids, context=None):
        self._check(cr, uid, ids, context=context)
        return super(account_journal_period, self).unlink(cr, uid, ids, context=context)

    _defaults = {
        'state': 'draft',
        'active': True,
    }
    _order = "period_id"

account_journal_period()

class account_fiscalyear(osv.osv):
    _inherit = "account.fiscalyear"
    _description = "Fiscal Year"
    _columns = {
        'end_journal_period_id':fields.many2one('account.journal.period','End of Year Entries Journal', readonly=True),
    }

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'period_ids': [],
            'end_journal_period_id': False
        })
        return super(account_fiscalyear, self).copy(cr, uid, id, default=default, context=context)

account_fiscalyear()
#----------------------------------------------------------
# Entries
#----------------------------------------------------------
class account_move(osv.osv):
    _name = "account.move"
    _description = "Account Entry"
    _order = 'id desc'

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        """
        Returns a list of tupples containing id, name, as internally it is called {def name_get}
        result format: {[(id, name), (id, name), ...]}

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param name: name to search
        @param args: other arguments
        @param operator: default operator is 'ilike', it can be changed
        @param context: context arguments, like lang, time zone
        @param limit: Returns first 'n' ids of complete result, default is 80.

        @return: Returns a list of tuples containing id and name
        """

        if not args:
          args = []
        ids = []
        if name:
            ids += self.search(cr, user, [('name','ilike',name)]+args, limit=limit, context=context)

        if not ids and name and type(name) == int:
            ids += self.search(cr, user, [('id','=',name)]+args, limit=limit, context=context)

        if not ids:
            ids += self.search(cr, user, args, limit=limit, context=context)

        return self.name_get(cr, user, ids, context=context)

    def name_get(self, cursor, user, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        res = []
        data_move = self.pool.get('account.move').browse(cursor, user, ids, context=context)
        for move in data_move:
            if move.state=='draft':
                name = '*' + str(move.id)
            else:
                name = move.name
            res.append((move.id, name))
        return res

    def _get_period(self, cr, uid, context=None):
        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        return False

    def _amount_compute(self, cr, uid, ids, name, args, context, where =''):
        if not ids: return {}
        cr.execute( 'SELECT move_id, SUM(debit) '\
                    'FROM account_move_line '\
                    'WHERE move_id IN %s '\
                    'GROUP BY move_id', (tuple(ids),))
        result = dict(cr.fetchall())
        for id in ids:
            result.setdefault(id, 0.0)
        return result

    def _search_amount(self, cr, uid, obj, name, args, context):
        ids = set()
        for cond in args:
            amount = cond[2]
            if isinstance(cond[2],(list,tuple)):
                if cond[1] in ['in','not in']:
                    amount = tuple(cond[2])
                else:
                    continue
            else:
                if cond[1] in ['=like', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of']:
                    continue

            cr.execute("select move_id from account_move_line group by move_id having sum(debit) %s %%s" % (cond[1]),(amount,))
            res_ids = set(id[0] for id in cr.fetchall())
            ids = ids and (ids & res_ids) or res_ids
        if ids:
            return [('id', 'in', tuple(ids))]
        return [('id', '=', '0')]

    _columns = {
        'name': fields.char('Number', size=64, required=True),
        'ref': fields.char('Reference', size=64),
        'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, states={'posted':[('readonly',True)]}),
        'state': fields.selection([('draft','Unposted'), ('posted','Posted')], 'Status', required=True, readonly=True,
            help='All manually created new journal entries are usually in the state \'Unposted\', but you can set the option to skip that state on the related journal. In that case, they will behave as journal entries automatically created by the system on document validation (invoices, bank statements...) and will be created in \'Posted\' state.'),
        'line_id': fields.one2many('account.move.line', 'move_id', 'Entries', states={'posted':[('readonly',True)]}),
        'to_check': fields.boolean('To Review', help='Check this box if you are unsure of that journal entry and if you want to note it as \'to be reviewed\' by an accounting expert.'),
        'partner_id': fields.related('line_id', 'partner_id', type="many2one", relation="res.partner", string="Partner", store=True),
        'amount': fields.function(_amount_compute, string='Amount', digits_compute=dp.get_precision('Account'), type='float', fnct_search=_search_amount),
        'date': fields.date('Date', required=True, states={'posted':[('readonly',True)]}, select=True),
        'narration':fields.text('Internal Note'),
        'company_id': fields.related('journal_id','company_id',type='many2one',relation='res.company',string='Company', store=True, readonly=True),
        'balance': fields.float('balance', digits_compute=dp.get_precision('Account'), help="This is a field only used for internal purpose and shouldn't be displayed"),
    }

    _defaults = {
        'name': '/',
        'state': 'draft',
        'period_id': _get_period,
        'date': fields.date.context_today,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def _check_centralisation(self, cursor, user, ids, context=None):
        for move in self.browse(cursor, user, ids, context=context):
            if move.journal_id.centralisation:
                move_ids = self.search(cursor, user, [
                    ('period_id', '=', move.period_id.id),
                    ('journal_id', '=', move.journal_id.id),
                    ])
                if len(move_ids) > 1:
                    return False
        return True

    _constraints = [
        (_check_centralisation,
            'You cannot create more than one move per period on a centralized journal.',
            ['journal_id']),
    ]

    def post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice = context.get('invoice', False)
        valid_moves = self.validate(cr, uid, ids, context)

        if not valid_moves:
            raise osv.except_osv(_('Error!'), _('You cannot validate a non-balanced entry.\nMake sure you have configured payment terms properly.\nThe latest payment term line should be of the "Balance" type.'))
        obj_sequence = self.pool.get('ir.sequence')
        for move in self.browse(cr, uid, valid_moves, context=context):
            if move.name =='/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.internal_number:
                    new_name = invoice.internal_number
                else:
                    if journal.sequence_id:
                        c = {'fiscalyear_id': move.period_id.fiscalyear_id.id}
                        new_name = obj_sequence.next_by_id(cr, uid, journal.sequence_id.id, c)
                    else:
                        raise osv.except_osv(_('Error!'), _('Please define a sequence on the journal.'))

                if new_name:
                    self.write(cr, uid, [move.id], {'name':new_name})

        cr.execute('UPDATE account_move '\
                   'SET state=%s '\
                   'WHERE id IN %s',
                   ('posted', tuple(valid_moves),))
        return True

    def button_validate(self, cursor, user, ids, context=None):
        for move in self.browse(cursor, user, ids, context=context):
            # check that all accounts have the same topmost ancestor
            top_common = None
            for line in move.line_id:
                account = line.account_id
                top_account = account
                while top_account.parent_id:
                    top_account = top_account.parent_id
                if not top_common:
                    top_common = top_account
                elif top_account.id != top_common.id:
                    raise osv.except_osv(_('Error!'),
                                         _('You cannot validate this journal entry because account "%s" does not belong to chart of accounts "%s".') % (account.name, top_common.name))
        return self.post(cursor, user, ids, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if not line.journal_id.update_posted:
                raise osv.except_osv(_('Error!'), _('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
        if ids:
            cr.execute('UPDATE account_move '\
                       'SET state=%s '\
                       'WHERE id IN %s', ('draft', tuple(ids),))
        return True

    def onchange_line_id(self, cr, uid, ids, line_ids, context=None):
        balance = 0.0
        for line in line_ids:
            if line[2]:
                balance += (line[2]['debit'] or 0.00)- (line[2]['credit'] or 0.00)
        return {'value': {'balance': balance}}

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        c = context.copy()
        c['novalidate'] = True
        result = super(account_move, self).write(cr, uid, ids, vals, c)
        self.validate(cr, uid, ids, context=context)
        return result

    #
    # TODO: Check if period is closed !
    #
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'line_id' in vals and context.get('copy'):
            for l in vals['line_id']:
                if not l[0]:
                    l[2].update({
                        'reconcile_id':False,
                        'reconcil_partial_id':False,
                        'analytic_lines':False,
                        'invoice':False,
                        'ref':False,
                        'balance':False,
                        'account_tax_id':False,
                    })

            if 'journal_id' in vals and vals.get('journal_id', False):
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['journal_id'] = vals['journal_id']
                context['journal_id'] = vals['journal_id']
            if 'period_id' in vals:
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = vals['period_id']
                context['period_id'] = vals['period_id']
            else:
                default_period = self._get_period(cr, uid, context)
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = default_period
                context['period_id'] = default_period

        if 'line_id' in vals:
            c = context.copy()
            c['novalidate'] = True
            result = super(account_move, self).create(cr, uid, vals, c)
            self.validate(cr, uid, [result], context)
        else:
            result = super(account_move, self).create(cr, uid, vals, context)
        return result

    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}
        default.update({
            'state':'draft',
            'name':'/',
        })
        context.update({
            'copy':True
        })
        return super(account_move, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}
        toremove = []
        obj_move_line = self.pool.get('account.move.line')
        for move in self.browse(cr, uid, ids, context=context):
            if move['state'] != 'draft':
                raise osv.except_osv(_('User Error!'),
                        _('You cannot delete a posted journal entry "%s".') % \
                                move['name'])
            line_ids = map(lambda x: x.id, move.line_id)
            context['journal_id'] = move.journal_id.id
            context['period_id'] = move.period_id.id
            obj_move_line._update_check(cr, uid, line_ids, context)
            obj_move_line.unlink(cr, uid, line_ids, context=context)
            toremove.append(move.id)
        result = super(account_move, self).unlink(cr, uid, toremove, context)
        return result

    def _compute_balance(self, cr, uid, id, context=None):
        move = self.browse(cr, uid, id, context=context)
        amount = 0
        for line in move.line_id:
            amount+= (line.debit - line.credit)
        return amount

    def _centralise(self, cr, uid, move, mode, context=None):
        assert mode in ('debit', 'credit'), 'Invalid Mode' #to prevent sql injection
        currency_obj = self.pool.get('res.currency')
        if context is None:
            context = {}

        if mode=='credit':
            account_id = move.journal_id.default_debit_account_id.id
            mode2 = 'debit'
            if not account_id:
                raise osv.except_osv(_('User Error!'),
                        _('There is no default debit account defined \n' \
                                'on journal "%s".') % move.journal_id.name)
        else:
            account_id = move.journal_id.default_credit_account_id.id
            mode2 = 'credit'
            if not account_id:
                raise osv.except_osv(_('User Error!'),
                        _('There is no default credit account defined \n' \
                                'on journal "%s".') % move.journal_id.name)

        # find the first line of this move with the current mode
        # or create it if it doesn't exist
        cr.execute('select id from account_move_line where move_id=%s and centralisation=%s limit 1', (move.id, mode))
        res = cr.fetchone()
        if res:
            line_id = res[0]
        else:
            context.update({'journal_id': move.journal_id.id, 'period_id': move.period_id.id})
            line_id = self.pool.get('account.move.line').create(cr, uid, {
                'name': _(mode.capitalize()+' Centralisation'),
                'centralisation': mode,
                'account_id': account_id,
                'move_id': move.id,
                'journal_id': move.journal_id.id,
                'period_id': move.period_id.id,
                'date': move.period_id.date_stop,
                'debit': 0.0,
                'credit': 0.0,
            }, context)

        # find the first line of this move with the other mode
        # so that we can exclude it from our calculation
        cr.execute('select id from account_move_line where move_id=%s and centralisation=%s limit 1', (move.id, mode2))
        res = cr.fetchone()
        if res:
            line_id2 = res[0]
        else:
            line_id2 = 0

        cr.execute('SELECT SUM(%s) FROM account_move_line WHERE move_id=%%s AND id!=%%s' % (mode,), (move.id, line_id2))
        result = cr.fetchone()[0] or 0.0
        cr.execute('update account_move_line set '+mode2+'=%s where id=%s', (result, line_id))

        #adjust also the amount in currency if needed
        cr.execute("select currency_id, sum(amount_currency) as amount_currency from account_move_line where move_id = %s and currency_id is not null group by currency_id", (move.id,))
        for row in cr.dictfetchall():
            currency_id = currency_obj.browse(cr, uid, row['currency_id'], context=context)
            if not currency_obj.is_zero(cr, uid, currency_id, row['amount_currency']):
                amount_currency = row['amount_currency'] * -1
                account_id = amount_currency > 0 and move.journal_id.default_debit_account_id.id or move.journal_id.default_credit_account_id.id
                cr.execute('select id from account_move_line where move_id=%s and centralisation=\'currency\' and currency_id = %slimit 1', (move.id, row['currency_id']))
                res = cr.fetchone()
                if res:
                    cr.execute('update account_move_line set amount_currency=%s , account_id=%s where id=%s', (amount_currency, account_id, res[0]))
                else:
                    context.update({'journal_id': move.journal_id.id, 'period_id': move.period_id.id})
                    line_id = self.pool.get('account.move.line').create(cr, uid, {
                        'name': _('Currency Adjustment'),
                        'centralisation': 'currency',
                        'account_id': account_id,
                        'move_id': move.id,
                        'journal_id': move.journal_id.id,
                        'period_id': move.period_id.id,
                        'date': move.period_id.date_stop,
                        'debit': 0.0,
                        'credit': 0.0,
                        'currency_id': row['currency_id'],
                        'amount_currency': amount_currency,
                    }, context)

        return True

    #
    # Validate a balanced move. If it is a centralised journal, create a move.
    #
    def validate(self, cr, uid, ids, context=None):
        if context and ('__last_update' in context):
            del context['__last_update']

        valid_moves = [] #Maintains a list of moves which can be responsible to create analytic entries
        obj_analytic_line = self.pool.get('account.analytic.line')
        obj_move_line = self.pool.get('account.move.line')
        for move in self.browse(cr, uid, ids, context):
            # Unlink old analytic lines on move_lines
            for obj_line in move.line_id:
                for obj in obj_line.analytic_lines:
                    obj_analytic_line.unlink(cr,uid,obj.id)

            journal = move.journal_id
            amount = 0
            line_ids = []
            line_draft_ids = []
            company_id = None
            for line in move.line_id:
                amount += line.debit - line.credit
                line_ids.append(line.id)
                if line.state=='draft':
                    line_draft_ids.append(line.id)

                if not company_id:
                    company_id = line.account_id.company_id.id
                if not company_id == line.account_id.company_id.id:
                    raise osv.except_osv(_('Error!'), _("Cannot create moves for different companies."))

                if line.account_id.currency_id and line.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id):
                        raise osv.except_osv(_('Error!'), _("""Cannot create move with currency different from ..""") % (line.account_id.code, line.account_id.name))

            if abs(amount) < 10 ** -4:
                # If the move is balanced
                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                # Check whether the move lines are confirmed

                if not line_draft_ids:
                    continue
                # Update the move lines (set them as valid)

                obj_move_line.write(cr, uid, line_draft_ids, {
                    'state': 'valid'
                }, context, check=False)

                account = {}
                account2 = {}

                if journal.type in ('purchase','sale'):
                    for line in move.line_id:
                        code = amount = 0
                        key = (line.account_id.id, line.tax_code_id.id)
                        if key in account2:
                            code = account2[key][0]
                            amount = account2[key][1] * (line.debit + line.credit)
                        elif line.account_id.id in account:
                            code = account[line.account_id.id][0]
                            amount = account[line.account_id.id][1] * (line.debit + line.credit)
                        if (code or amount) and not (line.tax_code_id or line.tax_amount):
                            obj_move_line.write(cr, uid, [line.id], {
                                'tax_code_id': code,
                                'tax_amount': amount
                            }, context, check=False)
            elif journal.centralisation:
                # If the move is not balanced, it must be centralised...

                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                #
                # Update the move lines (set them as valid)
                #
                self._centralise(cr, uid, move, 'debit', context=context)
                self._centralise(cr, uid, move, 'credit', context=context)
                obj_move_line.write(cr, uid, line_draft_ids, {
                    'state': 'valid'
                }, context, check=False)
            else:
                # We can't validate it (it's unbalanced)
                # Setting the lines as draft
                obj_move_line.write(cr, uid, line_ids, {
                    'state': 'draft'
                }, context, check=False)
        # Create analytic lines for the valid moves
        for record in valid_moves:
            obj_move_line.create_analytic_lines(cr, uid, [line.id for line in record.line_id], context)

        valid_moves = [move.id for move in valid_moves]
        return len(valid_moves) > 0 and valid_moves or False

account_move()

class account_move_reconcile(osv.osv):
    _name = "account.move.reconcile"
    _description = "Account Reconciliation"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type': fields.char('Type', size=16, required=True),
        'line_id': fields.one2many('account.move.line', 'reconcile_id', 'Entry Lines'),
        'line_partial_ids': fields.one2many('account.move.line', 'reconcile_partial_id', 'Partial Entry lines'),
        'create_date': fields.date('Creation date', readonly=True),
    }
    _defaults = {
        'name': lambda self,cr,uid,ctx=None: self.pool.get('ir.sequence').get(cr, uid, 'account.reconcile', context=ctx) or '/',
    }

    def reconcile_partial_check(self, cr, uid, ids, type='auto', context=None):
        total = 0.0
        for rec in self.browse(cr, uid, ids, context=context):
            for line in rec.line_partial_ids:
                if line.account_id.currency_id:
                    total += line.amount_currency
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0)
        if not total:
            self.pool.get('account.move.line').write(cr, uid,
                map(lambda x: x.id, rec.line_partial_ids),
                {'reconcile_id': rec.id }
            )
        return True

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []
        for r in self.browse(cr, uid, ids, context=context):
            total = reduce(lambda y,t: (t.debit or 0.0) - (t.credit or 0.0) + y, r.line_partial_ids, 0.0)
            if total:
                name = '%s (%.2f)' % (r.name, total)
                result.append((r.id,name))
            else:
                result.append((r.id,r.name))
        return result

account_move_reconcile()

#----------------------------------------------------------
# Tax
#----------------------------------------------------------
"""
a documenter
child_depend: la taxe depend des taxes filles
"""
class account_tax_code(osv.osv):
    """
    A code for the tax object.

    This code is used for some tax declarations.
    """
    def _sum(self, cr, uid, ids, name, args, context, where ='', where_params=()):
        parent_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)]))
        if context.get('based_on', 'invoices') == 'payments':
            cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.tax_code_id IN %s '+where+' \
                        AND move.id = line.move_id \
                        AND ((invoice.state = \'paid\') \
                            OR (invoice.id IS NULL)) \
                            GROUP BY line.tax_code_id',
                                (parent_ids,) + where_params)
        else:
            cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                    account_move AS move \
                    WHERE line.tax_code_id IN %s '+where+' \
                    AND move.id = line.move_id \
                    GROUP BY line.tax_code_id',
                       (parent_ids,) + where_params)
        res=dict(cr.fetchall())
        obj_precision = self.pool.get('decimal.precision')
        res2 = {}
        for record in self.browse(cr, uid, ids, context=context):
            def _rec_get(record):
                amount = res.get(record.id, 0.0)
                for rec in record.child_ids:
                    amount += _rec_get(rec) * rec.sign
                return amount
            res2[record.id] = round(_rec_get(record), obj_precision.precision_get(cr, uid, 'Account'))
        return res2

    def _sum_year(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        move_state = ('posted', )
        if context.get('state', 'all') == 'all':
            move_state = ('draft', 'posted', )
        if context.get('fiscalyear_id', False):
            fiscalyear_id = [context['fiscalyear_id']]
        else:
            fiscalyear_id = self.pool.get('account.fiscalyear').finds(cr, uid, exception=False)
        where = ''
        where_params = ()
        if fiscalyear_id:
            pids = []
            for fy in fiscalyear_id:
                pids += map(lambda x: str(x.id), self.pool.get('account.fiscalyear').browse(cr, uid, fy).period_ids)
            if pids:
                where = ' AND line.period_id IN %s AND move.state IN %s '
                where_params = (tuple(pids), move_state)
        return self._sum(cr, uid, ids, name, args, context,
                where=where, where_params=where_params)

    def _sum_period(self, cr, uid, ids, name, args, context):
        if context is None:
            context = {}
        move_state = ('posted', )
        if context.get('state', False) == 'all':
            move_state = ('draft', 'posted', )
        if context.get('period_id', False):
            period_id = context['period_id']
        else:
            period_id = self.pool.get('account.period').find(cr, uid)
            if not period_id:
                return dict.fromkeys(ids, 0.0)
            period_id = period_id[0]
        return self._sum(cr, uid, ids, name, args, context,
                where=' AND line.period_id=%s AND move.state IN %s', where_params=(period_id, move_state))

    _name = 'account.tax.code'
    _description = 'Tax Code'
    _rec_name = 'code'
    _columns = {
        'name': fields.char('Tax Case Name', size=64, required=True, translate=True),
        'code': fields.char('Case Code', size=64),
        'info': fields.text('Description'),
        'sum': fields.function(_sum_year, string="Year Sum"),
        'sum_period': fields.function(_sum_period, string="Period Sum"),
        'parent_id': fields.many2one('account.tax.code', 'Parent Code', select=True),
        'child_ids': fields.one2many('account.tax.code', 'parent_id', 'Child Codes'),
        'line_ids': fields.one2many('account.move.line', 'tax_code_id', 'Lines'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'sign': fields.float('Coefficent for parent', required=True, help='You can specify here the coefficient that will be used when consolidating the amount of this case into its parent. For example, set 1/-1 if you want to add/substract it.'),
        'notprintable':fields.boolean("Not Printable in Invoice", help="Check this box if you don't want any tax related to this tax code to appear on invoices"),
        'sequence': fields.integer('Sequence', help="Determine the display order in the report 'Accounting \ Reporting \ Generic Reporting \ Taxes \ Taxes Report'"),
    }

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = self.search(cr, user, ['|',('name',operator,name),('code',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','code'], context, load='_classic_write')
        return [(x['id'], (x['code'] and (x['code'] + ' - ') or '') + x['name']) \
                for x in reads]

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
    _defaults = {
        'company_id': _default_company,
        'sign': 1.0,
        'notprintable': False,
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'line_ids': []})
        return super(account_tax_code, self).copy(cr, uid, id, default, context)

    _check_recursion = check_cycle
    _constraints = [
        (_check_recursion, 'Error!\nYou cannot create recursive accounts.', ['parent_id'])
    ]
    _order = 'code'

account_tax_code()

class account_tax(osv.osv):
    """
    A tax object.

    Type: percent, fixed, none, code
        PERCENT: tax = price * amount
        FIXED: tax = price + amount
        NONE: no tax line
        CODE: execute python code. localcontext = {'price_unit':pu}
            return result in the context
            Ex: result=round(price_unit*0.21,4)
    """

    def get_precision_tax():
        def change_digit_tax(cr):
            res = pooler.get_pool(cr.dbname).get('decimal.precision').precision_get(cr, 1, 'Account')
            return (16, res+2)
        return change_digit_tax

    _name = 'account.tax'
    _description = 'Tax'
    _columns = {
        'name': fields.char('Tax Name', size=64, required=True, translate=True, help="This name will be displayed on reports"),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the tax lines from the lowest sequences to the higher ones. The order is important if you have a tax with several tax children. In this case, the evaluation order is important."),
        'amount': fields.float('Amount', required=True, digits_compute=get_precision_tax(), help="For taxes of type percentage, enter % ratio between 0-1."),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the tax without removing it."),
        'type': fields.selection( [('percent','Percentage'), ('fixed','Fixed Amount'), ('none','None'), ('code','Python Code'), ('balance','Balance')], 'Tax Type', required=True,
            help="The computation method for the tax amount."),
        'applicable_type': fields.selection( [('true','Always'), ('code','Given by Python Code')], 'Applicability', required=True,
            help="If not applicable (computed through a Python code), the tax won't appear on the invoice."),
        'domain':fields.char('Domain', size=32, help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain."),
        'account_collected_id':fields.many2one('account.account', 'Invoice Tax Account', help="Set the account that will be set by default on invoice tax lines for invoices. Leave empty to use the expense account."),
        'account_paid_id':fields.many2one('account.account', 'Refund Tax Account', help="Set the account that will be set by default on invoice tax lines for refunds. Leave empty to use the expense account."),
        'account_analytic_collected_id':fields.many2one('account.analytic.account', 'Invoice Tax Analytic Account', help="Set the analytic account that will be used by default on the invoice tax lines for invoices. Leave empty if you don't want to use an analytic account on the invoice tax lines by default."),
        'account_analytic_paid_id':fields.many2one('account.analytic.account', 'Refund Tax Analytic Account', help="Set the analytic account that will be used by default on the invoice tax lines for refunds. Leave empty if you don't want to use an analytic account on the invoice tax lines by default."),
        'parent_id':fields.many2one('account.tax', 'Parent Tax Account', select=True),
        'child_ids':fields.one2many('account.tax', 'parent_id', 'Child Tax Accounts'),
        'child_depend':fields.boolean('Tax on Children', help="Set if the tax computation is based on the computation of child taxes rather than on the total amount."),
        'python_compute':fields.text('Python Code'),
        'python_compute_inv':fields.text('Python Code (reverse)'),
        'python_applicable':fields.text('Python Code'),

        #
        # Fields used for the Tax declaration
        #
        'base_code_id': fields.many2one('account.tax.code', 'Account Base Code', help="Use this code for the tax declaration."),
        'tax_code_id': fields.many2one('account.tax.code', 'Account Tax Code', help="Use this code for the tax declaration."),
        'base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),

        # Same fields for refund invoices

        'ref_base_code_id': fields.many2one('account.tax.code', 'Refund Base Code', help="Use this code for the tax declaration."),
        'ref_tax_code_id': fields.many2one('account.tax.code', 'Refund Tax Code', help="Use this code for the tax declaration."),
        'ref_base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'ref_tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),
        'include_base_amount': fields.boolean('Included in base amount', help="Indicates if the amount of tax must be included in the base amount for the computation of the next taxes"),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'description': fields.char('Tax Code',size=32),
        'price_include': fields.boolean('Tax Included in Price', help="Check this if the price you use on the product and invoices includes this tax."),
        'type_tax_use': fields.selection([('sale','Sale'),('purchase','Purchase'),('all','All')], 'Tax Application', required=True)

    }
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Tax Name must be unique per company!'),
    ]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        """
        Returns a list of tupples containing id, name, as internally it is called {def name_get}
        result format: {[(id, name), (id, name), ...]}

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param name: name to search
        @param args: other arguments
        @param operator: default operator is 'ilike', it can be changed
        @param context: context arguments, like lang, time zone
        @param limit: Returns first 'n' ids of complete result, default is 80.

        @return: Returns a list of tupples containing id and name
        """
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('description', '=', name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context or {})
        return self.name_get(cr, user, ids, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('type', False) and vals['type'] in ('none', 'code'):
            vals.update({'amount': 0.0})
        return super(account_tax, self).write(cr, uid, ids, vals, context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        journal_pool = self.pool.get('account.journal')

        if context and context.has_key('type'):
            if context.get('type') in ('out_invoice','out_refund'):
                args += [('type_tax_use','in',['sale','all'])]
            elif context.get('type') in ('in_invoice','in_refund'):
                args += [('type_tax_use','in',['purchase','all'])]

        if context and context.has_key('journal_id'):
            journal = journal_pool.browse(cr, uid, context.get('journal_id'))
            if journal.type in ('sale', 'purchase'):
                args += [('type_tax_use','in',[journal.type,'all'])]

        return super(account_tax, self).search(cr, uid, args, offset, limit, order, context, count)

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.read(cr, uid, ids, ['description','name'], context=context):
            name = record['description'] and record['description'] or record['name']
            res.append((record['id'],name ))
        return res

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]

    _defaults = {
        'python_compute': '''# price_unit\n# or False\n# product: product.product object or None\n# partner: res.partner object or None\n\nresult = price_unit * 0.10''',
        'python_compute_inv': '''# price_unit\n# product: product.product object or False\n\nresult = price_unit * 0.10''',
        'applicable_type': 'true',
        'type': 'percent',
        'amount': 0,
        'price_include': 0,
        'active': 1,
        'type_tax_use': 'all',
        'sequence': 1,
        'ref_tax_sign': 1,
        'ref_base_sign': 1,
        'tax_sign': 1,
        'base_sign': 1,
        'include_base_amount': False,
        'company_id': _default_company,
    }
    _order = 'sequence'

    def _applicable(self, cr, uid, taxes, price_unit, product=None, partner=None):
        res = []
        for tax in taxes:
            if tax.applicable_type=='code':
                localdict = {'price_unit':price_unit, 'product':product, 'partner':partner}
                exec tax.python_applicable in localdict
                if localdict.get('result', False):
                    res.append(tax)
            else:
                res.append(tax)
        return res

    def _unit_compute(self, cr, uid, taxes, price_unit, product=None, partner=None, quantity=0):
        taxes = self._applicable(cr, uid, taxes, price_unit ,product, partner)
        res = []
        cur_price_unit=price_unit
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result
            data = {'id':tax.id,
                    'name':tax.description and tax.description + " - " + tax.name or tax.name,
                    'account_collected_id':tax.account_collected_id.id,
                    'account_paid_id':tax.account_paid_id.id,
                    'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                    'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                    'base_code_id': tax.base_code_id.id,
                    'ref_base_code_id': tax.ref_base_code_id.id,
                    'sequence': tax.sequence,
                    'base_sign': tax.base_sign,
                    'tax_sign': tax.tax_sign,
                    'ref_base_sign': tax.ref_base_sign,
                    'ref_tax_sign': tax.ref_tax_sign,
                    'price_unit': cur_price_unit,
                    'tax_code_id': tax.tax_code_id.id,
                    'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
            if tax.type=='percent':
                amount = cur_price_unit * tax.amount
                data['amount'] = amount

            elif tax.type=='fixed':
                data['amount'] = tax.amount
                data['tax_amount']=quantity
               # data['amount'] = quantity
            elif tax.type=='code':
                localdict = {'price_unit':cur_price_unit, 'product':product, 'partner':partner}
                exec tax.python_compute in localdict
                amount = localdict['result']
                data['amount'] = amount
            elif tax.type=='balance':
                data['amount'] = cur_price_unit - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)
                data['balance'] = cur_price_unit

            amount2 = data.get('amount', 0.0)
            if tax.child_ids:
                if tax.child_depend:
                    latest = res.pop()
                amount = amount2
                child_tax = self._unit_compute(cr, uid, tax.child_ids, amount, product, partner, quantity)
                res.extend(child_tax)
                if tax.child_depend:
                    for r in res:
                        for name in ('base','ref_base'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['price_unit'] = latest['price_unit']
                                latest[name+'_code_id'] = False
                        for name in ('tax','ref_tax'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['amount'] = data['amount']
                                latest[name+'_code_id'] = False
            if tax.include_base_amount:
                cur_price_unit+=amount2
        return res

    def compute_all(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, force_excluded=False):
        """
        :param force_excluded: boolean used to say that we don't want to consider the value of field price_include of
            tax. It's used in encoding by line where you don't matter if you encoded a tax with that boolean to True or
            False
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        tax_compute_precision = precision
        if taxes and taxes[0].company_id.tax_calculation_rounding_method == 'round_globally':
            tax_compute_precision += 5
        totalin = totalex = float_round(price_unit * quantity, precision)
        tin = []
        tex = []
        for tax in taxes:
            if not tax.price_include or force_excluded:
                tex.append(tax)
            else:
                tin.append(tax)
        tin = self.compute_inv(cr, uid, tin, price_unit, quantity, product=product, partner=partner, precision=tax_compute_precision)
        for r in tin:
            totalex -= r.get('amount', 0.0)
        totlex_qty = 0.0
        try:
            totlex_qty = totalex/quantity
        except:
            pass
        tex = self._compute(cr, uid, tex, totlex_qty, quantity, product=product, partner=partner, precision=tax_compute_precision)
        for r in tex:
            totalin += r.get('amount', 0.0)
        return {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }

    def compute(self, cr, uid, taxes, price_unit, quantity,  product=None, partner=None):
        _logger.warning("Deprecated, use compute_all(...)['taxes'] instead of compute(...) to manage prices with tax included.")
        return self._compute(cr, uid, taxes, price_unit, quantity, product, partner)

    def _compute(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, precision=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute(cr, uid, taxes, price_unit, product, partner, quantity)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r.get('balance', 0.0) * quantity, precision) - total
            else:
                r['amount'] = round(r.get('amount', 0.0) * quantity, precision)
                total += r['amount']
        return res

    def _unit_compute_inv(self, cr, uid, taxes, price_unit, product=None, partner=None):
        taxes = self._applicable(cr, uid, taxes, price_unit,  product, partner)
        res = []
        taxes.reverse()
        cur_price_unit = price_unit

        tax_parent_tot = 0.0
        for tax in taxes:
            if (tax.type=='percent') and not tax.include_base_amount:
                tax_parent_tot += tax.amount

        for tax in taxes:
            if (tax.type=='fixed') and not tax.include_base_amount:
                cur_price_unit -= tax.amount

        for tax in taxes:
            if tax.type=='percent':
                if tax.include_base_amount:
                    amount = cur_price_unit - (cur_price_unit / (1 + tax.amount))
                else:
                    amount = (cur_price_unit / (1 + tax_parent_tot)) * tax.amount

            elif tax.type=='fixed':
                amount = tax.amount

            elif tax.type=='code':
                localdict = {'price_unit':cur_price_unit, 'product':product, 'partner':partner}
                exec tax.python_compute_inv in localdict
                amount = localdict['result']
            elif tax.type=='balance':
                amount = cur_price_unit - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)

            if tax.include_base_amount:
                cur_price_unit -= amount
                todo = 0
            else:
                todo = 1
            res.append({
                'id': tax.id,
                'todo': todo,
                'name': tax.name,
                'amount': amount,
                'account_collected_id': tax.account_collected_id.id,
                'account_paid_id': tax.account_paid_id.id,
                'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'sequence': tax.sequence,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            })
            if tax.child_ids:
                if tax.child_depend:
                    del res[-1]
                    amount = price_unit

            parent_tax = self._unit_compute_inv(cr, uid, tax.child_ids, amount, product, partner)
            res.extend(parent_tax)

        total = 0.0
        for r in res:
            if r['todo']:
                total += r['amount']
        for r in res:
            r['price_unit'] -= total
            r['todo'] = 0
        return res

    def compute_inv(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, precision=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.
        Price Unit is a Tax included price

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute_inv(cr, uid, taxes, price_unit, product, partner=None)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r['balance'] * quantity, precision) - total
            else:
                r['amount'] = round(r['amount'] * quantity, precision)
                total += r['amount']
        return res

account_tax()

# ---------------------------------------------------------
# Account Entries Models
# ---------------------------------------------------------

class account_model(osv.osv):
    _name = "account.model"
    _description = "Account Model"
    _columns = {
        'name': fields.char('Model Name', size=64, required=True, help="This is a model for recurring accounting entries"),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'company_id': fields.related('journal_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'lines_id': fields.one2many('account.model.line', 'model_id', 'Model Entries'),
        'legend': fields.text('Legend', readonly=True, size=100),
    }

    _defaults = {
        'legend': lambda self, cr, uid, context:_('You can specify year, month and date in the name of the model using the following labels:\n\n%(year)s: To Specify Year \n%(month)s: To Specify Month \n%(date)s: Current Date\n\ne.g. My model on %(date)s'),
    }
    def generate(self, cr, uid, ids, datas={}, context=None):
        move_ids = []
        entry = {}
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        pt_obj = self.pool.get('account.payment.term')
        period_obj = self.pool.get('account.period')

        if context is None:
            context = {}

        if datas.get('date', False):
            context.update({'date': datas['date']})

        move_date = context.get('date', time.strftime('%Y-%m-%d'))
        move_date = datetime.strptime(move_date,"%Y-%m-%d")
        for model in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            ctx.update({'company_id': model.company_id.id})
            period_ids = period_obj.find(cr, uid, dt=context.get('date', False), context=ctx)
            period_id = period_ids and period_ids[0] or False
            ctx.update({'journal_id': model.journal_id.id,'period_id': period_id})
            try:
                entry['name'] = model.name%{'year': move_date.strftime('%Y'), 'month': move_date.strftime('%m'), 'date': move_date.strftime('%Y-%m')}
            except:
                raise osv.except_osv(_('Wrong model !'), _('You have a wrong expression "%(...)s" in your model !'))
            move_id = account_move_obj.create(cr, uid, {
                'ref': entry['name'],
                'period_id': period_id,
                'journal_id': model.journal_id.id,
                'date': context.get('date', fields.date.context_today(self,cr,uid,context=context))
            })
            move_ids.append(move_id)
            for line in model.lines_id:
                analytic_account_id = False
                if line.analytic_account_id:
                    if not model.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (model.journal_id.name,))
                    analytic_account_id = line.analytic_account_id.id
                val = {
                    'move_id': move_id,
                    'journal_id': model.journal_id.id,
                    'period_id': period_id,
                    'analytic_account_id': analytic_account_id
                }

                date_maturity = context.get('date',time.strftime('%Y-%m-%d'))
                if line.date_maturity == 'partner':
                    if not line.partner_id:
                        raise osv.except_osv(_('Error!'), _("Maturity date of entry line generated by model line '%s' of model '%s' is based on partner payment term!" \
                                                                "\nPlease define partner on it!")%(line.name, model.name))
                    if line.partner_id.property_payment_term:
                        payment_term_id = line.partner_id.property_payment_term.id
                        pterm_list = pt_obj.compute(cr, uid, payment_term_id, value=1, date_ref=date_maturity)
                        if pterm_list:
                            pterm_list = [l[0] for l in pterm_list]
                            pterm_list.sort()
                            date_maturity = pterm_list[-1]

                val.update({
                    'name': line.name,
                    'quantity': line.quantity,
                    'debit': line.debit,
                    'credit': line.credit,
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.partner_id.id,
                    'date': context.get('date', fields.date.context_today(self,cr,uid,context=context)),
                    'date_maturity': date_maturity
                })
                account_move_line_obj.create(cr, uid, val, context=ctx)

        return move_ids

account_model()

class account_model_line(osv.osv):
    _name = "account.model.line"
    _description = "Account Model Entries"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the resources from lower sequences to higher ones."),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Account'), help="The optional quantity on entries."),
        'debit': fields.float('Debit', digits_compute=dp.get_precision('Account')),
        'credit': fields.float('Credit', digits_compute=dp.get_precision('Account')),
        'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade"),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', ondelete="cascade"),
        'model_id': fields.many2one('account.model', 'Model', required=True, ondelete="cascade", select=True),
        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency."),
        'currency_id': fields.many2one('res.currency', 'Currency'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'date_maturity': fields.selection([('today','Date of the day'), ('partner','Partner Payment Term')], 'Maturity Date', help="The maturity date of the generated entries for this model. You can choose between the creation date or the creation date of the entries plus the partner payment terms."),
    }
    _order = 'sequence'
    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in model, they must be positive!'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in model, they must be positive!'),
    ]
account_model_line()

# ---------------------------------------------------------
# Account Subscription
# ---------------------------------------------------------


class account_subscription(osv.osv):
    _name = "account.subscription"
    _description = "Account Subscription"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'ref': fields.char('Reference', size=16),
        'model_id': fields.many2one('account.model', 'Model', required=True),
        'date_start': fields.date('Start Date', required=True),
        'period_total': fields.integer('Number of Periods', required=True),
        'period_nbr': fields.integer('Period', required=True),
        'period_type': fields.selection([('day','days'),('month','month'),('year','year')], 'Period Type', required=True),
        'state': fields.selection([('draft','Draft'),('running','Running'),('done','Done')], 'Status', required=True, readonly=True),
        'lines_id': fields.one2many('account.subscription.line', 'subscription_id', 'Subscription Lines')
    }
    _defaults = {
        'date_start': fields.date.context_today,
        'period_type': 'month',
        'period_total': 12,
        'period_nbr': 1,
        'state': 'draft',
    }
    def state_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'})
        return False

    def check(self, cr, uid, ids, context=None):
        todone = []
        for sub in self.browse(cr, uid, ids, context=context):
            ok = True
            for line in sub.lines_id:
                if not line.move_id.id:
                    ok = False
                    break
            if ok:
                todone.append(sub.id)
        if todone:
            self.write(cr, uid, todone, {'state':'done'})
        return False

    def remove_line(self, cr, uid, ids, context=None):
        toremove = []
        for sub in self.browse(cr, uid, ids, context=context):
            for line in sub.lines_id:
                if not line.move_id.id:
                    toremove.append(line.id)
        if toremove:
            self.pool.get('account.subscription.line').unlink(cr, uid, toremove)
        self.write(cr, uid, ids, {'state':'draft'})
        return False

    def compute(self, cr, uid, ids, context=None):
        for sub in self.browse(cr, uid, ids, context=context):
            ds = sub.date_start
            for i in range(sub.period_total):
                self.pool.get('account.subscription.line').create(cr, uid, {
                    'date': ds,
                    'subscription_id': sub.id,
                })
                if sub.period_type=='day':
                    ds = (datetime.strptime(ds, '%Y-%m-%d') + relativedelta(days=sub.period_nbr)).strftime('%Y-%m-%d')
                if sub.period_type=='month':
                    ds = (datetime.strptime(ds, '%Y-%m-%d') + relativedelta(months=sub.period_nbr)).strftime('%Y-%m-%d')
                if sub.period_type=='year':
                    ds = (datetime.strptime(ds, '%Y-%m-%d') + relativedelta(years=sub.period_nbr)).strftime('%Y-%m-%d')
        self.write(cr, uid, ids, {'state':'running'})
        return True

account_subscription()

class account_subscription_line(osv.osv):
    _name = "account.subscription.line"
    _description = "Account Subscription Line"
    _columns = {
        'subscription_id': fields.many2one('account.subscription', 'Subscription', required=True, select=True),
        'date': fields.date('Date', required=True),
        'move_id': fields.many2one('account.move', 'Entry'),
    }

    def move_create(self, cr, uid, ids, context=None):
        tocheck = {}
        all_moves = []
        obj_model = self.pool.get('account.model')
        for line in self.browse(cr, uid, ids, context=context):
            datas = {
                'date': line.date,
            }
            move_ids = obj_model.generate(cr, uid, [line.subscription_id.model_id.id], datas, context)
            tocheck[line.subscription_id.id] = True
            self.write(cr, uid, [line.id], {'move_id':move_ids[0]})
            all_moves.extend(move_ids)
        if tocheck:
            self.pool.get('account.subscription').check(cr, uid, tocheck.keys(), context)
        return all_moves

    _rec_name = 'date'

account_subscription_line()

#  ---------------------------------------------------------------
#   Account Templates: Account, Tax, Tax Code and chart. + Wizard
#  ---------------------------------------------------------------

class account_tax_template(osv.osv):
    _name = 'account.tax.template'
account_tax_template()

class account_account_template(osv.osv):
    _order = "code"
    _name = "account.account.template"
    _description ='Templates for Accounts'

    _columns = {
        'name': fields.char('Name', size=256, required=True, select=True),
        'currency_id': fields.many2one('res.currency', 'Secondary Currency', help="Forces all moves for this account to have this secondary currency."),
        'code': fields.char('Code', size=64, required=True, select=1),
        'type': fields.selection([
            ('receivable','Receivable'),
            ('payable','Payable'),
            ('view','View'),
            ('consolidation','Consolidation'),
            ('liquidity','Liquidity'),
            ('other','Regular'),
            ('closed','Closed'),
            ], 'Internal Type', required=True,help="This type is used to differentiate types with "\
            "special effects in OpenERP: view can not have entries, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts."),
        'user_type': fields.many2one('account.account.type', 'Account Type', required=True,
            help="These types are defined according to your country. The type contains more information "\
            "about the account and its specificities."),
        'financial_report_ids': fields.many2many('account.financial.report', 'account_template_financial_report', 'account_template_id', 'report_line_id', 'Financial Reports'),
        'reconcile': fields.boolean('Allow Reconciliation', help="Check this option if you want the user to reconcile entries in this account."),
        'shortcut': fields.char('Shortcut', size=12),
        'note': fields.text('Note'),
        'parent_id': fields.many2one('account.account.template', 'Parent Account Template', ondelete='cascade'),
        'child_parent_ids':fields.one2many('account.account.template', 'parent_id', 'Children'),
        'tax_ids': fields.many2many('account.tax.template', 'account_account_template_tax_rel', 'account_id', 'tax_id', 'Default Taxes'),
        'nocreate': fields.boolean('Optional create', help="If checked, the new chart of accounts will not contain this by default."),
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', help="This optional field allow you to link an account template to a specific chart template that may differ from the one its root parent belongs to. This allow you to define chart templates that extend another and complete it with few new accounts (You don't need to define the whole structure that is common to both several times)."),
    }

    _defaults = {
        'reconcile': False,
        'type': 'view',
        'nocreate': False,
    }

    def _check_type(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        accounts = self.browse(cr, uid, ids, context=context)
        for account in accounts:
            if account.parent_id and account.parent_id.type != 'view':
                return False
        return True

    _check_recursion = check_cycle
    _constraints = [
        (_check_recursion, 'Error!\nYou cannot create recursive account templates.', ['parent_id']),
        (_check_type, 'Configuration Error!\nYou cannot define children to an account that has internal type other than  "View".', ['type']),

    ]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name','code'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code']+' '+name
            res.append((record['id'],name ))
        return res

    def generate_account(self, cr, uid, chart_template_id, tax_template_ref, acc_template_ref, code_digits, company_id, context=None):
        """
        This method for generating accounts from templates.

        :param chart_template_id: id of the chart template chosen in the wizard
        :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
        :paramacc_template_ref: dictionary with the mappping between the account templates and the real accounts.
        :param code_digits: number of digits got from wizard.multi.charts.accounts, this is use for account code.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: return acc_template_ref for reference purpose.
        :rtype: dict
        """
        if context is None:
            context = {}
        obj_acc = self.pool.get('account.account')
        company_name = self.pool.get('res.company').browse(cr, uid, company_id, context=context).name
        template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
        #deactivate the parent_store functionnality on account_account for rapidity purpose
        ctx = context.copy()
        ctx.update({'defer_parent_store_computation': True})
        level_ref = {}
        children_acc_criteria = [('chart_template_id','=', chart_template_id)]
        if template.account_root_id.id:
            children_acc_criteria = ['|'] + children_acc_criteria + ['&',('parent_id','child_of', [template.account_root_id.id]),('chart_template_id','=', False)]
        children_acc_template = self.search(cr, uid, [('nocreate','!=',True)] + children_acc_criteria, order='id')
        for account_template in self.browse(cr, uid, children_acc_template, context=context):
            # skip the root of COA if it's not the main one
            if (template.account_root_id.id == account_template.id) and template.parent_id:
                continue
            tax_ids = []
            for tax in account_template.tax_ids:
                tax_ids.append(tax_template_ref[tax.id])

            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main > 0 and code_main <= code_digits and account_template.type != 'view':
                code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
            parent_id = account_template.parent_id and ((account_template.parent_id.id in acc_template_ref) and acc_template_ref[account_template.parent_id.id]) or False
            #the level as to be given as well at the creation time, because of the defer_parent_store_computation in
            #context. Indeed because of this, the parent_left and parent_right are not computed and thus the child_of
            #operator does not return the expected values, with result of having the level field not computed at all.
            if parent_id:
                level = parent_id in level_ref and level_ref[parent_id] + 1 or obj_acc._get_level(cr, uid, [parent_id], 'level', None, context=context)[parent_id] + 1
            else:
                level = 0
            vals={
                'name': (template.account_root_id.id == account_template.id) and company_name or account_template.name,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'type': account_template.type,
                'user_type': account_template.user_type and account_template.user_type.id or False,
                'reconcile': account_template.reconcile,
                'shortcut': account_template.shortcut,
                'note': account_template.note,
                'financial_report_ids': account_template.financial_report_ids and [(6,0,[x.id for x in account_template.financial_report_ids])] or False,
                'parent_id': parent_id,
                'tax_ids': [(6,0,tax_ids)],
                'company_id': company_id,
                'level': level,
            }
            new_account = obj_acc.create(cr, uid, vals, context=ctx)
            acc_template_ref[account_template.id] = new_account
            level_ref[new_account] = level

        #reactivate the parent_store functionnality on account_account
        obj_acc._parent_store_compute(cr)
        return acc_template_ref

account_account_template()

class account_add_tmpl_wizard(osv.osv_memory):
    """Add one more account from the template.

    With the 'nocreate' option, some accounts may not be created. Use this to add them later."""
    _name = 'account.addtmpl.wizard'

    def _get_def_cparent(self, cr, uid, context=None):
        acc_obj = self.pool.get('account.account')
        tmpl_obj = self.pool.get('account.account.template')
        tids = tmpl_obj.read(cr, uid, [context['tmpl_ids']], ['parent_id'])
        if not tids or not tids[0]['parent_id']:
            return False
        ptids = tmpl_obj.read(cr, uid, [tids[0]['parent_id'][0]], ['code'])
        res = None
        if not ptids or not ptids[0]['code']:
            raise osv.except_osv(_('Error!'), _('There is no parent code for the template account.'))
            res = acc_obj.search(cr, uid, [('code','=',ptids[0]['code'])])
        return res and res[0] or False

    _columns = {
        'cparent_id':fields.many2one('account.account', 'Parent target', help="Creates an account with the selected template under this existing parent.", required=True),
    }
    _defaults = {
        'cparent_id': _get_def_cparent,
    }

    def action_create(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        acc_obj = self.pool.get('account.account')
        tmpl_obj = self.pool.get('account.account.template')
        data = self.read(cr, uid, ids)[0]
        company_id = acc_obj.read(cr, uid, [data['cparent_id'][0]], ['company_id'])[0]['company_id'][0]
        account_template = tmpl_obj.browse(cr, uid, context['tmpl_ids'])
        vals = {
            'name': account_template.name,
            'currency_id': account_template.currency_id and account_template.currency_id.id or False,
            'code': account_template.code,
            'type': account_template.type,
            'user_type': account_template.user_type and account_template.user_type.id or False,
            'reconcile': account_template.reconcile,
            'shortcut': account_template.shortcut,
            'note': account_template.note,
            'parent_id': data['cparent_id'][0],
            'company_id': company_id,
            }
        acc_obj.create(cr, uid, vals)
        return {'type':'state', 'state': 'end' }

    def action_cancel(self, cr, uid, ids, context=None):
        return { 'type': 'state', 'state': 'end' }

account_add_tmpl_wizard()

class account_tax_code_template(osv.osv):

    _name = 'account.tax.code.template'
    _description = 'Tax Code Template'
    _order = 'code'
    _rec_name = 'code'
    _columns = {
        'name': fields.char('Tax Case Name', size=64, required=True),
        'code': fields.char('Case Code', size=64),
        'info': fields.text('Description'),
        'parent_id': fields.many2one('account.tax.code.template', 'Parent Code', select=True),
        'child_ids': fields.one2many('account.tax.code.template', 'parent_id', 'Child Codes'),
        'sign': fields.float('Sign For Parent', required=True),
        'notprintable':fields.boolean("Not Printable in Invoice", help="Check this box if you don't want any tax related to this tax Code to appear on invoices."),
    }

    _defaults = {
        'sign': 1.0,
        'notprintable': False,
    }

    def generate_tax_code(self, cr, uid, tax_code_root_id, company_id, context=None):
        '''
        This function generates the tax codes from the templates of tax code that are children of the given one passed
        in argument. Then it returns a dictionary with the mappping between the templates and the real objects.

        :param tax_code_root_id: id of the root of all the tax code templates to process
        :param company_id: id of the company the wizard is running for
        :returns: dictionary with the mappping between the templates and the real objects.
        :rtype: dict
        '''
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_tax_code = self.pool.get('account.tax.code')
        tax_code_template_ref = {}
        company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)

        #find all the children of the tax_code_root_id
        children_tax_code_template = tax_code_root_id and obj_tax_code_template.search(cr, uid, [('parent_id','child_of',[tax_code_root_id])], order='id') or []
        for tax_code_template in obj_tax_code_template.browse(cr, uid, children_tax_code_template, context=context):
            vals = {
                'name': (tax_code_root_id == tax_code_template.id) and company.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False,
                'company_id': company_id,
                'sign': tax_code_template.sign,
            }
            #check if this tax code already exists
            rec_list = obj_tax_code.search(cr, uid, [('name', '=', vals['name']),('code', '=', vals['code']),('company_id', '=', vals['company_id'])], context=context)
            if not rec_list:
                #if not yet, create it
                new_tax_code = obj_tax_code.create(cr, uid, vals)
                #recording the new tax code to do the mapping
                tax_code_template_ref[tax_code_template.id] = new_tax_code
        return tax_code_template_ref

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','code'], context, load='_classic_write')
        return [(x['id'], (x['code'] and x['code'] + ' - ' or '') + x['name']) \
                for x in reads]

    _check_recursion = check_cycle
    _constraints = [
        (_check_recursion, 'Error!\nYou cannot create recursive Tax Codes.', ['parent_id'])
    ]
    _order = 'code,name'
account_tax_code_template()


class account_chart_template(osv.osv):
    _name="account.chart.template"
    _description= "Templates for Account Chart"

    _columns={
        'name': fields.char('Name', size=64, required=True),
        'parent_id': fields.many2one('account.chart.template', 'Parent Chart Template'),
        'code_digits': fields.integer('# of Digits', required=True, help="No. of Digits to use for account code"),
        'visible': fields.boolean('Can be Visible?', help="Set this to False if you don't want this template to be used actively in the wizard that generate Chart of Accounts from templates, this is useful when you want to generate accounts of this template only when loading its child template."),
        'complete_tax_set': fields.boolean('Complete Set of Taxes', help='This boolean helps you to choose if you want to propose to the user to encode the sale and purchase rates or choose from list of taxes. This last choice assumes that the set of tax defined on this template is complete'),
        'account_root_id': fields.many2one('account.account.template', 'Root Account', domain=[('parent_id','=',False)]),
        'tax_code_root_id': fields.many2one('account.tax.code.template', 'Root Tax Code', domain=[('parent_id','=',False)]),
        'tax_template_ids': fields.one2many('account.tax.template', 'chart_template_id', 'Tax Template List', help='List of all the taxes that have to be installed by the wizard'),
        'bank_account_view_id': fields.many2one('account.account.template', 'Bank Account'),
        'property_account_receivable': fields.many2one('account.account.template', 'Receivable Account'),
        'property_account_payable': fields.many2one('account.account.template', 'Payable Account'),
        'property_account_expense_categ': fields.many2one('account.account.template', 'Expense Category Account'),
        'property_account_income_categ': fields.many2one('account.account.template', 'Income Category Account'),
        'property_account_expense': fields.many2one('account.account.template', 'Expense Account on Product Template'),
        'property_account_income': fields.many2one('account.account.template', 'Income Account on Product Template'),
        'property_reserve_and_surplus_account': fields.many2one('account.account.template', 'Reserve and Profit/Loss Account', domain=[('type', '=', 'payable')], help='This Account is used for transferring Profit/Loss(If It is Profit: Amount will be added, Loss: Amount will be deducted.), Which is calculated from Profilt & Loss Report'),
        'property_account_income_opening': fields.many2one('account.account.template', 'Opening Entries Income Account'),
        'property_account_expense_opening': fields.many2one('account.account.template', 'Opening Entries Expense Account'),
    }

    _defaults = {
        'visible': True,
        'code_digits': 6,
        'complete_tax_set': True,
    }

account_chart_template()

class account_tax_template(osv.osv):

    _name = 'account.tax.template'
    _description = 'Templates for Taxes'

    _columns = {
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', required=True),
        'name': fields.char('Tax Name', size=64, required=True),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the taxes lines from lower sequences to higher ones. The order is important if you have a tax that has several tax children. In this case, the evaluation order is important."),
        'amount': fields.float('Amount', required=True, digits=(14,4), help="For Tax Type percent enter % ratio between 0-1."),
        'type': fields.selection( [('percent','Percent'), ('fixed','Fixed'), ('none','None'), ('code','Python Code'), ('balance','Balance')], 'Tax Type', required=True),
        'applicable_type': fields.selection( [('true','True'), ('code','Python Code')], 'Applicable Type', required=True, help="If not applicable (computed through a Python code), the tax won't appear on the invoice."),
        'domain':fields.char('Domain', size=32, help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain."),
        'account_collected_id':fields.many2one('account.account.template', 'Invoice Tax Account'),
        'account_paid_id':fields.many2one('account.account.template', 'Refund Tax Account'),
        'parent_id':fields.many2one('account.tax.template', 'Parent Tax Account', select=True),
        'child_depend':fields.boolean('Tax on Children', help="Set if the tax computation is based on the computation of child taxes rather than on the total amount."),
        'python_compute':fields.text('Python Code'),
        'python_compute_inv':fields.text('Python Code (reverse)'),
        'python_applicable':fields.text('Python Code'),

        #
        # Fields used for the Tax declaration
        #
        'base_code_id': fields.many2one('account.tax.code.template', 'Base Code', help="Use this code for the tax declaration."),
        'tax_code_id': fields.many2one('account.tax.code.template', 'Tax Code', help="Use this code for the tax declaration."),
        'base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),

        # Same fields for refund invoices

        'ref_base_code_id': fields.many2one('account.tax.code.template', 'Refund Base Code', help="Use this code for the tax declaration."),
        'ref_tax_code_id': fields.many2one('account.tax.code.template', 'Refund Tax Code', help="Use this code for the tax declaration."),
        'ref_base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'ref_tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),
        'include_base_amount': fields.boolean('Include in Base Amount', help="Set if the amount of tax must be included in the base amount before computing the next taxes."),
        'description': fields.char('Internal Name', size=32),
        'type_tax_use': fields.selection([('sale','Sale'),('purchase','Purchase'),('all','All')], 'Tax Use In', required=True,),
        'price_include': fields.boolean('Tax Included in Price', help="Check this if the price you use on the product and invoices includes this tax."),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.read(cr, uid, ids, ['description','name'], context=context):
            name = record['description'] and record['description'] or record['name']
            res.append((record['id'],name ))
        return res

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]

    _defaults = {
        'python_compute': lambda *a: '''# price_unit\n# product: product.product object or None\n# partner: res.partner object or None\n\nresult = price_unit * 0.10''',
        'python_compute_inv': lambda *a: '''# price_unit\n# product: product.product object or False\n\nresult = price_unit * 0.10''',
        'applicable_type': 'true',
        'type': 'percent',
        'amount': 0,
        'sequence': 1,
        'ref_tax_sign': 1,
        'ref_base_sign': 1,
        'tax_sign': 1,
        'base_sign': 1,
        'include_base_amount': False,
        'type_tax_use': 'all',
        'price_include': 0,
    }
    _order = 'sequence'

    def _generate_tax(self, cr, uid, tax_templates, tax_code_template_ref, company_id, context=None):
        """
        This method generate taxes from templates.

        :param tax_templates: list of browse record of the tax templates to process
        :param tax_code_template_ref: Taxcode templates reference.
        :param company_id: id of the company the wizard is running for
        :returns:
            {
            'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
            'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        if context is None:
            context = {}
        res = {}
        todo_dict = {}
        tax_template_to_tax = {}
        for tax in tax_templates:
            vals_tax = {
                'name':tax.name,
                'sequence': tax.sequence,
                'amount': tax.amount,
                'type': tax.type,
                'applicable_type': tax.applicable_type,
                'domain': tax.domain,
                'parent_id': tax.parent_id and ((tax.parent_id.id in tax_template_to_tax) and tax_template_to_tax[tax.parent_id.id]) or False,
                'child_depend': tax.child_depend,
                'python_compute': tax.python_compute,
                'python_compute_inv': tax.python_compute_inv,
                'python_applicable': tax.python_applicable,
                'base_code_id': tax.base_code_id and ((tax.base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.base_code_id.id]) or False,
                'tax_code_id': tax.tax_code_id and ((tax.tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.tax_code_id.id]) or False,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_code_id': tax.ref_base_code_id and ((tax.ref_base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_base_code_id.id]) or False,
                'ref_tax_code_id': tax.ref_tax_code_id and ((tax.ref_tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_tax_code_id.id]) or False,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'include_base_amount': tax.include_base_amount,
                'description': tax.description,
                'company_id': company_id,
                'type_tax_use': tax.type_tax_use,
                'price_include': tax.price_include
            }
            new_tax = self.pool.get('account.tax').create(cr, uid, vals_tax)
            tax_template_to_tax[tax.id] = new_tax
            #as the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax] = {
                'account_collected_id': tax.account_collected_id and tax.account_collected_id.id or False,
                'account_paid_id': tax.account_paid_id and tax.account_paid_id.id or False,
            }
        res.update({'tax_template_to_tax': tax_template_to_tax, 'account_dict': todo_dict})
        return res

account_tax_template()

# Fiscal Position Templates

class account_fiscal_position_template(osv.osv):
    _name = 'account.fiscal.position.template'
    _description = 'Template for Fiscal Position'

    _columns = {
        'name': fields.char('Fiscal Position Template', size=64, required=True),
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', required=True),
        'account_ids': fields.one2many('account.fiscal.position.account.template', 'position_id', 'Account Mapping'),
        'tax_ids': fields.one2many('account.fiscal.position.tax.template', 'position_id', 'Tax Mapping'),
        'note': fields.text('Notes', translate=True),
    }

    def generate_fiscal_position(self, cr, uid, chart_temp_id, tax_template_ref, acc_template_ref, company_id, context=None):
        """
        This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

        :param chart_temp_id: Chart Template Id.
        :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
        :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        if context is None:
            context = {}
        obj_tax_fp = self.pool.get('account.fiscal.position.tax')
        obj_ac_fp = self.pool.get('account.fiscal.position.account')
        obj_fiscal_position = self.pool.get('account.fiscal.position')
        fp_ids = self.search(cr, uid, [('chart_template_id', '=', chart_temp_id)])
        for position in self.browse(cr, uid, fp_ids, context=context):
            new_fp = obj_fiscal_position.create(cr, uid, {'company_id': company_id, 'name': position.name, 'note': position.note})
            for tax in position.tax_ids:
                obj_tax_fp.create(cr, uid, {
                    'tax_src_id': tax_template_ref[tax.tax_src_id.id],
                    'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                    'position_id': new_fp
                })
            for acc in position.account_ids:
                obj_ac_fp.create(cr, uid, {
                    'account_src_id': acc_template_ref[acc.account_src_id.id],
                    'account_dest_id': acc_template_ref[acc.account_dest_id.id],
                    'position_id': new_fp
                })
        return True

account_fiscal_position_template()

class account_fiscal_position_tax_template(osv.osv):
    _name = 'account.fiscal.position.tax.template'
    _description = 'Template Tax Fiscal Position'
    _rec_name = 'position_id'

    _columns = {
        'position_id': fields.many2one('account.fiscal.position.template', 'Fiscal Position', required=True, ondelete='cascade'),
        'tax_src_id': fields.many2one('account.tax.template', 'Tax Source', required=True),
        'tax_dest_id': fields.many2one('account.tax.template', 'Replacement Tax')
    }

account_fiscal_position_tax_template()

class account_fiscal_position_account_template(osv.osv):
    _name = 'account.fiscal.position.account.template'
    _description = 'Template Account Fiscal Mapping'
    _rec_name = 'position_id'
    _columns = {
        'position_id': fields.many2one('account.fiscal.position.template', 'Fiscal Mapping', required=True, ondelete='cascade'),
        'account_src_id': fields.many2one('account.account.template', 'Account Source', domain=[('type','<>','view')], required=True),
        'account_dest_id': fields.many2one('account.account.template', 'Account Destination', domain=[('type','<>','view')], required=True)
    }

account_fiscal_position_account_template()

# ---------------------------------------------------------
# Account generation from template wizards
# ---------------------------------------------------------

class wizard_multi_charts_accounts(osv.osv_memory):
    """
    Create a new account chart for a company.
    Wizards ask for:
        * a company
        * an account chart template
        * a number of digits for formatting code of non-view accounts
        * a list of bank accounts owned by the company
    Then, the wizard:
        * generates all accounts from the template and assigns them to the right company
        * generates all taxes and tax codes, changing account assignations
        * generates all accounting properties and assigns them correctly
    """
    _name='wizard.multi.charts.accounts'
    _inherit = 'res.config'

    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=True),
        'only_one_chart_template': fields.boolean('Only One Chart Template Available'),
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', required=True),
        'bank_accounts_id': fields.one2many('account.bank.accounts.wizard', 'bank_account_id', 'Cash and Banks', required=True),
        'code_digits':fields.integer('# of Digits', required=True, help="No. of Digits to use for account code"),
        "sale_tax": fields.many2one("account.tax.template", "Default Sale Tax"),
        "purchase_tax": fields.many2one("account.tax.template", "Default Purchase Tax"),
        'sale_tax_rate': fields.float('Sales Tax(%)'),
        'purchase_tax_rate': fields.float('Purchase Tax(%)'),
        'complete_tax_set': fields.boolean('Complete Set of Taxes', help='This boolean helps you to choose if you want to propose to the user to encode the sales and purchase rates or use the usual m2o fields. This last choice assumes that the set of tax defined for the chosen template is complete'),
    }
    def onchange_tax_rate(self, cr, uid, ids, rate=False, context=None):
        return {'value': {'purchase_tax_rate': rate or False}}

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id=False, context=None):
        res = {}
        tax_templ_obj = self.pool.get('account.tax.template')
        res['value'] = {'complete_tax_set': False, 'sale_tax': False, 'purchase_tax': False}
        if chart_template_id:
            data = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
            res['value'].update({'complete_tax_set': data.complete_tax_set})
            if data.complete_tax_set:
            # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                sale_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                              , "=", chart_template_id), ('type_tax_use', 'in', ('sale','all'))], order="sequence, id desc")
                purchase_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                              , "=", chart_template_id), ('type_tax_use', 'in', ('purchase','all'))], order="sequence, id desc")
                res['value'].update({'sale_tax': sale_tax_ids and sale_tax_ids[0] or False, 'purchase_tax': purchase_tax_ids and purchase_tax_ids[0] or False})

            if data.code_digits:
               res['value'].update({'code_digits': data.code_digits})
        return res

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_multi_charts_accounts, self).default_get(cr, uid, fields, context=context)
        tax_templ_obj = self.pool.get('account.tax.template')

        if 'bank_accounts_id' in fields:
            res.update({'bank_accounts_id': [{'acc_name': _('Cash'), 'account_type': 'cash'},{'acc_name': _('Bank'), 'account_type': 'bank'}]})
        if 'company_id' in fields:
            res.update({'company_id': self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0].company_id.id})

        ids = self.pool.get('account.chart.template').search(cr, uid, [('visible', '=', True)], context=context)
        if ids:
            if 'chart_template_id' in fields:
                res.update({'only_one_chart_template': len(ids) == 1, 'chart_template_id': ids[0]})
            if 'sale_tax' in fields:
                sale_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                              , "=", ids[0]), ('type_tax_use', 'in', ('sale','all'))], order="sequence")
                res.update({'sale_tax': sale_tax_ids and sale_tax_ids[0] or False})
            if 'purchase_tax' in fields:
                purchase_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                          , "=", ids[0]), ('type_tax_use', 'in', ('purchase','all'))], order="sequence")
                res.update({'purchase_tax': purchase_tax_ids and purchase_tax_ids[0] or False})
        res.update({
            'purchase_tax_rate': 15.0,
            'sale_tax_rate': 15.0,
        })
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:context = {}
        res = super(wizard_multi_charts_accounts, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        cmp_select = []
        acc_template_obj = self.pool.get('account.chart.template')
        company_obj = self.pool.get('res.company')

        company_ids = company_obj.search(cr, uid, [], context=context)
        #display in the widget selection of companies, only the companies that haven't been configured yet (but don't care about the demo chart of accounts)
        cr.execute("SELECT company_id FROM account_account WHERE active = 't' AND account_account.parent_id IS NULL AND name != %s", ("Chart For Automated Tests",))
        configured_cmp = [r[0] for r in cr.fetchall()]
        unconfigured_cmp = list(set(company_ids)-set(configured_cmp))
        for field in res['fields']:
            if field == 'company_id':
                res['fields'][field]['domain'] = [('id','in',unconfigured_cmp)]
                res['fields'][field]['selection'] = [('', '')]
                if unconfigured_cmp:
                    cmp_select = [(line.id, line.name) for line in company_obj.browse(cr, uid, unconfigured_cmp)]
                    res['fields'][field]['selection'] = cmp_select
        return res

    def check_created_journals(self, cr, uid, vals_journal, company_id, context=None):
        """
        This method used for checking journals already created or not. If not then create new journal.
        """
        obj_journal = self.pool.get('account.journal')
        rec_list = obj_journal.search(cr, uid, [('name','=', vals_journal['name']),('company_id', '=', company_id)], context=context)
        if not rec_list:
            obj_journal.create(cr, uid, vals_journal, context=context)
        return True

    def generate_journals(self, cr, uid, chart_template_id, acc_template_ref, company_id, context=None):
        """
        This method is used for creating journals.

        :param chart_temp_id: Chart Template Id.
        :param acc_template_ref: Account templates reference.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        journal_data = self._prepare_all_journals(cr, uid, chart_template_id, acc_template_ref, company_id, context=context)
        for vals_journal in journal_data:
            self.check_created_journals(cr, uid, vals_journal, company_id, context=context)
        return True

    def _prepare_all_journals(self, cr, uid, chart_template_id, acc_template_ref, company_id, context=None):
        def _get_analytic_journal(journal_type):
            # Get the analytic journal
            data = False
            if journal_type in ('sale', 'sale_refund'):
                data = obj_data.get_object_reference(cr, uid, 'account', 'analytic_journal_sale')
            elif journal_type in ('purchase', 'purchase_refund'):
                pass
            elif journal_type == 'general':
                pass
            return data and data[1] or False

        def _get_default_account(journal_type, type='debit'):
            # Get the default accounts
            default_account = False
            if journal_type in ('sale', 'sale_refund'):
                default_account = acc_template_ref.get(template.property_account_income_categ.id)
            elif journal_type in ('purchase', 'purchase_refund'):
                default_account = acc_template_ref.get(template.property_account_expense_categ.id)
            elif journal_type == 'situation':
                if type == 'debit':
                    default_account = acc_template_ref.get(template.property_account_expense_opening.id)
                else:
                    default_account = acc_template_ref.get(template.property_account_income_opening.id)
            return default_account

        def _get_view_id(journal_type):
            # Get the journal views
            if journal_type in ('general', 'situation'):
                data = obj_data.get_object_reference(cr, uid, 'account', 'account_journal_view')
            elif journal_type in ('sale_refund', 'purchase_refund'):
                data = obj_data.get_object_reference(cr, uid, 'account', 'account_sp_refund_journal_view')
            else:
                data = obj_data.get_object_reference(cr, uid, 'account', 'account_sp_journal_view')
            return data and data[1] or False

        journal_names = {
            'sale': _('Sales Journal'),
            'purchase': _('Purchase Journal'),
            'sale_refund': _('Sales Refund Journal'),
            'purchase_refund': _('Purchase Refund Journal'),
            'general': _('Miscellaneous Journal'),
            'situation': _('Opening Entries Journal'),
        }
        journal_codes = {
            'sale': _('SAJ'),
            'purchase': _('EXJ'),
            'sale_refund': _('SCNJ'),
            'purchase_refund': _('ECNJ'),
            'general': _('MISC'),
            'situation': _('OPEJ'),
        }

        obj_data = self.pool.get('ir.model.data')
        analytic_journal_obj = self.pool.get('account.analytic.journal')
        template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)

        journal_data = []
        for journal_type in ['sale', 'purchase', 'sale_refund', 'purchase_refund', 'general', 'situation']:
            vals = {
                'type': journal_type,
                'name': journal_names[journal_type],
                'code': journal_codes[journal_type],
                'company_id': company_id,
                'centralisation': journal_type == 'situation',
                'view_id': _get_view_id(journal_type),
                'analytic_journal_id': _get_analytic_journal(journal_type),
                'default_credit_account_id': _get_default_account(journal_type, 'credit'),
                'default_debit_account_id': _get_default_account(journal_type, 'debit'),
            }
            journal_data.append(vals)
        return journal_data

    def generate_properties(self, cr, uid, chart_template_id, acc_template_ref, company_id, context=None):
        """
        This method used for creating properties.

        :param chart_template_id: id of the current chart template for which we need to create properties
        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        property_obj = self.pool.get('ir.property')
        field_obj = self.pool.get('ir.model.fields')
        todo_list = [
            ('property_account_receivable','res.partner','account.account'),
            ('property_account_payable','res.partner','account.account'),
            ('property_account_expense_categ','product.category','account.account'),
            ('property_account_income_categ','product.category','account.account'),
            ('property_account_expense','product.template','account.account'),
            ('property_account_income','product.template','account.account'),
            ('property_reserve_and_surplus_account','res.company','account.account')
        ]
        template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
        for record in todo_list:
            account = getattr(template, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = field_obj.search(cr, uid, [('name', '=', record[0]),('model', '=', record[1]),('relation', '=', record[2])], context=context)
                vals = {
                    'name': record[0],
                    'company_id': company_id,
                    'fields_id': field[0],
                    'value': value,
                }
                property_ids = property_obj.search(cr, uid, [('name','=', record[0]),('company_id', '=', company_id)], context=context)
                if property_ids:
                    #the property exist: modify it
                    property_obj.write(cr, uid, property_ids, vals, context=context)
                else:
                    #create the property
                    property_obj.create(cr, uid, vals, context=context)
        return True

    def _install_template(self, cr, uid, template_id, company_id, code_digits=None, obj_wizard=None, acc_ref={}, taxes_ref={}, tax_code_ref={}, context=None):
        '''
        This function recursively loads the template objects and create the real objects from them.

        :param template_id: id of the chart template to load
        :param company_id: id of the company the wizard is running for
        :param code_digits: integer that depicts the number of digits the accounts code should have in the COA
        :param obj_wizard: the current wizard for generating the COA from the templates
        :param acc_ref: Mapping between ids of account templates and real accounts created from them
        :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
        :param tax_code_ref: Mapping between ids of tax code templates and real tax codes created from them
        :returns: return a tuple with a dictionary containing
            * the mapping between the account template ids and the ids of the real accounts that have been generated
              from them, as first item,
            * a similar dictionary for mapping the tax templates and taxes, as second item,
            * a last identical containing the mapping of tax code templates and tax codes
        :rtype: tuple(dict, dict, dict)
        '''
        template = self.pool.get('account.chart.template').browse(cr, uid, template_id, context=context)
        if template.parent_id:
            tmp1, tmp2, tmp3 = self._install_template(cr, uid, template.parent_id.id, company_id, code_digits=code_digits, acc_ref=acc_ref, taxes_ref=taxes_ref, tax_code_ref=tax_code_ref, context=context)
            acc_ref.update(tmp1)
            taxes_ref.update(tmp2)
            tax_code_ref.update(tmp3)
        tmp1, tmp2, tmp3 = self._load_template(cr, uid, template_id, company_id, code_digits=code_digits, obj_wizard=obj_wizard, account_ref=acc_ref, taxes_ref=taxes_ref, tax_code_ref=tax_code_ref, context=context)
        acc_ref.update(tmp1)
        taxes_ref.update(tmp2)
        tax_code_ref.update(tmp3)
        return acc_ref, taxes_ref, tax_code_ref

    def _load_template(self, cr, uid, template_id, company_id, code_digits=None, obj_wizard=None, account_ref={}, taxes_ref={}, tax_code_ref={}, context=None):
        '''
        This function generates all the objects from the templates

        :param template_id: id of the chart template to load
        :param company_id: id of the company the wizard is running for
        :param code_digits: integer that depicts the number of digits the accounts code should have in the COA
        :param obj_wizard: the current wizard for generating the COA from the templates
        :param acc_ref: Mapping between ids of account templates and real accounts created from them
        :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
        :param tax_code_ref: Mapping between ids of tax code templates and real tax codes created from them
        :returns: return a tuple with a dictionary containing
            * the mapping between the account template ids and the ids of the real accounts that have been generated
              from them, as first item,
            * a similar dictionary for mapping the tax templates and taxes, as second item,
            * a last identical containing the mapping of tax code templates and tax codes
        :rtype: tuple(dict, dict, dict)
        '''
        template = self.pool.get('account.chart.template').browse(cr, uid, template_id, context=context)
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_acc_tax = self.pool.get('account.tax')
        obj_tax_temp = self.pool.get('account.tax.template')
        obj_acc_template = self.pool.get('account.account.template')
        obj_fiscal_position_template = self.pool.get('account.fiscal.position.template')

        # create all the tax code.
        tax_code_ref.update(obj_tax_code_template.generate_tax_code(cr, uid, template.tax_code_root_id.id, company_id, context=context))

        # Generate taxes from templates.
        tax_templates = [x for x in template.tax_template_ids]
        generated_tax_res = obj_tax_temp._generate_tax(cr, uid, tax_templates, tax_code_ref, company_id, context=context)
        taxes_ref.update(generated_tax_res['tax_template_to_tax'])

        # Generating Accounts from templates.
        account_template_ref = obj_acc_template.generate_account(cr, uid, template_id, taxes_ref, account_ref, code_digits, company_id, context=context)
        account_ref.update(account_template_ref)

        # writing account values on tax after creation of accounts
        for key,value in generated_tax_res['account_dict'].items():
            if value['account_collected_id'] or value['account_paid_id']:
                obj_acc_tax.write(cr, uid, [key], {
                    'account_collected_id': account_ref.get(value['account_collected_id'], False),
                    'account_paid_id': account_ref.get(value['account_paid_id'], False),
                })

        # Create Journals
        self.generate_journals(cr, uid, template_id, account_ref, company_id, context=context)

        # generate properties function
        self.generate_properties(cr, uid, template_id, account_ref, company_id, context=context)

        # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
        obj_fiscal_position_template.generate_fiscal_position(cr, uid, template_id, taxes_ref, account_ref, company_id, context=context)

        return account_ref, taxes_ref, tax_code_ref

    def _create_tax_templates_from_rates(self, cr, uid, obj_wizard, company_id, context=None):
        '''
        This function checks if the chosen chart template is configured as containing a full set of taxes, and if
        it's not the case, it creates the templates for account.tax.code and for account.account.tax objects accordingly
        to the provided sale/purchase rates. Then it saves the new tax templates as default taxes to use for this chart
        template.

        :param obj_wizard: browse record of wizard to generate COA from templates
        :param company_id: id of the company for wich the wizard is running
        :return: True
        '''
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_tax_temp = self.pool.get('account.tax.template')
        chart_template = obj_wizard.chart_template_id
        vals = {}
        # get the ids of all the parents of the selected account chart template
        current_chart_template = chart_template
        all_parents = [current_chart_template.id]
        while current_chart_template.parent_id:
            current_chart_template = current_chart_template.parent_id
            all_parents.append(current_chart_template.id)
        # create tax templates and tax code templates from purchase_tax_rate and sale_tax_rate fields
        if not chart_template.complete_tax_set:
            value = obj_wizard.sale_tax_rate
            ref_tax_ids = obj_tax_temp.search(cr, uid, [('type_tax_use','in', ('sale','all')), ('chart_template_id', 'in', all_parents)], context=context, order="sequence, id desc", limit=1)
            obj_tax_temp.write(cr, uid, ref_tax_ids, {'amount': value/100.0, 'name': _('Tax %.2f%%') % value})
            value = obj_wizard.purchase_tax_rate
            ref_tax_ids = obj_tax_temp.search(cr, uid, [('type_tax_use','in', ('purchase','all')), ('chart_template_id', 'in', all_parents)], context=context, order="sequence, id desc", limit=1)
            obj_tax_temp.write(cr, uid, ref_tax_ids, {'amount': value/100.0, 'name': _('Purchase Tax %.2f%%') % value})
        return True

    def execute(self, cr, uid, ids, context=None):
        '''
        This function is called at the confirmation of the wizard to generate the COA from the templates. It will read
        all the provided information to create the accounts, the banks, the journals, the taxes, the tax codes, the
        accounting properties... accordingly for the chosen company.
        '''
        ir_values_obj = self.pool.get('ir.values')
        obj_wizard = self.browse(cr, uid, ids[0])
        company_id = obj_wizard.company_id.id
        # If the floats for sale/purchase rates have been filled, create templates from them
        self._create_tax_templates_from_rates(cr, uid, obj_wizard, company_id, context=context)

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref, tax_code_ref = self._install_template(cr, uid, obj_wizard.chart_template_id.id, company_id, code_digits=obj_wizard.code_digits, obj_wizard=obj_wizard, context=context)

        # write values of default taxes for product
        if obj_wizard.sale_tax and taxes_ref:
            ir_values_obj.set(cr, uid, key='default', key2=False, name="taxes_id", company=company_id,
                                models =[('product.product',False)], value=[taxes_ref[obj_wizard.sale_tax.id]])
        if obj_wizard.purchase_tax and taxes_ref:
                ir_values_obj.set(cr, uid, key='default', key2=False, name="supplier_taxes_id", company=company_id,
                                models =[('product.product',False)], value=[taxes_ref[obj_wizard.purchase_tax.id]])

        # Create Bank journals
        self._create_bank_journals_from_o2m(cr, uid, obj_wizard, company_id, acc_template_ref, context=context)
        return {}

    def _prepare_bank_journal(self, cr, uid, line, current_num, default_account_id, company_id, context=None):
        '''
        This function prepares the value to use for the creation of a bank journal created through the wizard of
        generating COA from templates.

        :param line: dictionary containing the values encoded by the user related to his bank account
        :param current_num: integer corresponding to a counter of the already created bank journals through this wizard.
        :param default_account_id: id of the default debit.credit account created before for this journal.
        :param company_id: id of the company for which the wizard is running
        :return: mapping of field names and values
        :rtype: dict
        '''
        obj_data = self.pool.get('ir.model.data')
        obj_journal = self.pool.get('account.journal')
        # Get the id of journal views
        tmp = obj_data.get_object_reference(cr, uid, 'account', 'account_journal_bank_view_multi')
        view_id_cur = tmp and tmp[1] or False
        tmp = obj_data.get_object_reference(cr, uid, 'account', 'account_journal_bank_view')
        view_id_cash = tmp and tmp[1] or False

        # we need to loop again to find next number for journal code
        # because we can't rely on the value current_num as,
        # its possible that we already have bank journals created (e.g. by the creation of res.partner.bank)
        # and the next number for account code might have been already used before for journal
        for num in xrange(current_num, 100):
            # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
            journal_code = _('BNK')[:3] + str(num)
            ids = obj_journal.search(cr, uid, [('code', '=', journal_code), ('company_id', '=', company_id)], context=context)
            if not ids:
                break
        else:
            raise osv.except_osv(_('Error!'), _('Cannot generate an unused journal code.'))

        vals = {
                'name': line['acc_name'],
                'code': journal_code,
                'type': line['account_type'] == 'cash' and 'cash' or 'bank',
                'company_id': company_id,
                'analytic_journal_id': False,
                'currency': False,
                'default_credit_account_id': default_account_id,
                'default_debit_account_id': default_account_id,
        }
        if line['currency_id']:
            vals['view_id'] = view_id_cur
            vals['currency'] = line['currency_id']
        else:
            vals['view_id'] = view_id_cash
        return vals

    def _prepare_bank_account(self, cr, uid, line, new_code, acc_template_ref, ref_acc_bank, company_id, context=None):
        '''
        This function prepares the value to use for the creation of the default debit and credit accounts of a
        bank journal created through the wizard of generating COA from templates.

        :param line: dictionary containing the values encoded by the user related to his bank account
        :param new_code: integer corresponding to the next available number to use as account code
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :param ref_acc_bank: browse record of the account template set as root of all bank accounts for the chosen
            template
        :param company_id: id of the company for which the wizard is running
        :return: mapping of field names and values
        :rtype: dict
        '''
        obj_data = self.pool.get('ir.model.data')

        # Get the id of the user types fr-or cash and bank
        tmp = obj_data.get_object_reference(cr, uid, 'account', 'data_account_type_cash')
        cash_type = tmp and tmp[1] or False
        tmp = obj_data.get_object_reference(cr, uid, 'account', 'data_account_type_bank')
        bank_type = tmp and tmp[1] or False
        return {
                'name': line['acc_name'],
                'currency_id': line['currency_id'],
                'code': new_code,
                'type': 'liquidity',
                'user_type': line['account_type'] == 'cash' and cash_type or bank_type,
                'parent_id': acc_template_ref[ref_acc_bank.id] or False,
                'company_id': company_id,
        }

    def _create_bank_journals_from_o2m(self, cr, uid, obj_wizard, company_id, acc_template_ref, context=None):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_accounts_id of the
        wizard.

        :param obj_wizard: the current wizard that generates the COA from the templates.
        :param company_id: the id of the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :return: True
        '''
        obj_acc = self.pool.get('account.account')
        obj_journal = self.pool.get('account.journal')
        code_digits = obj_wizard.code_digits

        # Build a list with all the data to process
        journal_data = []
        if obj_wizard.bank_accounts_id:
            for acc in obj_wizard.bank_accounts_id:
                vals = {
                    'acc_name': acc.acc_name,
                    'account_type': acc.account_type,
                    'currency_id': acc.currency_id.id,
                }
                journal_data.append(vals)
        ref_acc_bank = obj_wizard.chart_template_id.bank_account_view_id
        if journal_data and not ref_acc_bank.code:
            raise osv.except_osv(_('Configuration Error!'), _('You have to set a code for the bank account defined on the selected chart of accounts.'))

        current_num = 1
        for line in journal_data:
            # Seek the next available number for the account code
            while True:
                new_code = str(ref_acc_bank.code.ljust(code_digits-len(str(current_num)), '0')) + str(current_num)
                ids = obj_acc.search(cr, uid, [('code', '=', new_code), ('company_id', '=', company_id)])
                if not ids:
                    break
                else:
                    current_num += 1
            # Create the default debit/credit accounts for this bank journal
            vals = self._prepare_bank_account(cr, uid, line, new_code, acc_template_ref, ref_acc_bank, company_id, context=context)
            default_account_id  = obj_acc.create(cr, uid, vals, context=context)

            #create the bank journal
            vals_journal = self._prepare_bank_journal(cr, uid, line, current_num, default_account_id, company_id, context=context)
            obj_journal.create(cr, uid, vals_journal)
            current_num += 1
        return True

wizard_multi_charts_accounts()

class account_bank_accounts_wizard(osv.osv_memory):
    _name='account.bank.accounts.wizard'

    _columns = {
        'acc_name': fields.char('Account Name.', size=64, required=True),
        'bank_account_id': fields.many2one('wizard.multi.charts.accounts', 'Bank Account', required=True),
        'currency_id': fields.many2one('res.currency', 'Secondary Currency', help="Forces all moves for this account to have this secondary currency."),
        'account_type': fields.selection([('cash','Cash'), ('check','Check'), ('bank','Bank')], 'Account Type', size=32),
    }

account_bank_accounts_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
