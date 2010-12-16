# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
import netsvc
from osv import fields, osv
from tools.translate import _

import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

import tools

class account_move_line(osv.osv):
    _name = "account.move.line"
    _description = "Entry lines"

    def _query_get(self, cr, uid, obj='l', context={}):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        if not context.get('fiscalyear', False):
            fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
            fiscalyear_clause = (','.join([str(x) for x in fiscalyear_ids])) or '0'
        else:
            fiscalyear_clause = '%s' % context['fiscalyear']
        state=context.get('state',False)
        where_move_state = ''
        where_move_lines_by_date = ''

        if context.get('date_from', False) and context.get('date_to', False):
            where_move_lines_by_date = " AND " +obj+".move_id in ( select id from account_move  where date >= '" +context['date_from']+"' AND date <= '"+context['date_to']+"')"
            
        if state:
            if state.lower() not in ['all']:
                where_move_state= " AND "+obj+".move_id in (select id from account_move where account_move.state = '"+state+"')"
        
                
        if context.get('periods', False):
            ids = ','.join([str(x) for x in context['periods']])
            return obj+".state<>'draft' AND "+obj+".period_id in (SELECT id from account_period WHERE fiscalyear_id in (%s) AND id in (%s)) %s %s" % (fiscalyear_clause, ids,where_move_state,where_move_lines_by_date)
        else:
            return obj+".state<>'draft' AND "+obj+".period_id in (SELECT id from account_period WHERE fiscalyear_id in (%s) %s %s)" % (fiscalyear_clause,where_move_state,where_move_lines_by_date)

    def default_get(self, cr, uid, fields, context={}):
        data = self._default_get(cr, uid, fields, context)
        for f in data.keys():
            if f not in fields:
                del data[f]
        return data

    def create_analytic_lines(self, cr, uid, ids, context={}):
        for obj_line in self.browse(cr, uid, ids, context):
            if obj_line.analytic_account_id:
                if not obj_line.journal_id.analytic_journal_id:
                    raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (obj_line.journal_id.name,))
                amt = (obj_line.credit or  0.0) - (obj_line.debit or 0.0)
                vals_lines={
                    'name': obj_line.name,
                    'date': obj_line.date,
                    'account_id': obj_line.analytic_account_id.id,
                    'unit_amount':obj_line.quantity,
                    'product_id': obj_line.product_id and obj_line.product_id.id or False,
                    'product_uom_id': obj_line.product_uom_id and obj_line.product_uom_id.id or False,
                    'amount': amt,
                    'general_account_id': obj_line.account_id.id,
                    'journal_id': obj_line.journal_id.analytic_journal_id.id,
                    'ref': obj_line.ref,
                    'move_id':obj_line.id
                }
                new_id = self.pool.get('account.analytic.line').create(cr,uid,vals_lines)
        return True

    def _default_get_move_form_hook(self, cursor, user, data):
        '''Called in the end of default_get method for manual entry in account_move form'''
        if data.has_key('analytic_account_id'):
            del(data['analytic_account_id'])
        if data.has_key('account_tax_id'):
            del(data['account_tax_id'])
        return data

    def _default_get(self, cr, uid, fields, context={}):
        # Compute simple values
        data = super(account_move_line, self).default_get(cr, uid, fields, context)
        # Starts: Manual entry from account.move form
        if context.get('lines',[]):

            total_new=0.00
            for i in context['lines']:
                if i[2]:
                    total_new +=(i[2]['debit'] or 0.00)- (i[2]['credit'] or 0.00)
                    for item in i[2]:
                            data[item]=i[2][item]
            if context['journal']:
                journal_obj=self.pool.get('account.journal').browse(cr,uid,context['journal'])
                if journal_obj.type == 'purchase':
                    if total_new>0:
                        account = journal_obj.default_credit_account_id
                    else:
                        account = journal_obj.default_debit_account_id
                else:
                    if total_new>0:
                        account = journal_obj.default_credit_account_id
                    else:
                        account = journal_obj.default_debit_account_id


                if account and ((not fields) or ('debit' in fields) or ('credit' in fields)) and 'partner_id' in data and (data['partner_id']):
                    part = self.pool.get('res.partner').browse(cr, uid, data['partner_id'])
                    account = self.pool.get('account.fiscal.position').map_account(cr, uid, part and part.property_account_position or False, account.id)
                    account = self.pool.get('account.account').browse(cr, uid, account)
                    data['account_id'] =  account.id

            s = -total_new
            data['debit'] = s>0  and s or 0.0
            data['credit'] = s<0  and -s or 0.0
            data = self._default_get_move_form_hook(cr, uid, data)
            return data
        # Ends: Manual entry from account.move form

        if not 'move_id' in fields: #we are not in manual entry
            return data

        period_obj = self.pool.get('account.period')

        # Compute the current move
        move_id = False
        partner_id = False
        if context.get('journal_id',False) and context.get('period_id',False):
            if 'move_id' in fields:
                cr.execute('select move_id \
                    from \
                        account_move_line \
                    where \
                        journal_id=%s and period_id=%s and create_uid=%s and state=%s \
                    order by id desc limit 1',
                    (context['journal_id'], context['period_id'], uid, 'draft'))
                res = cr.fetchone()
                move_id = (res and res[0]) or False

                if not move_id:
                    return data
                else:
                    data['move_id'] = move_id
            if 'date' in fields:
                cr.execute('select date  \
                    from \
                        account_move_line \
                    where \
                        journal_id=%s and period_id=%s and create_uid=%s \
                    order by id desc',
                    (context['journal_id'], context['period_id'], uid))
                res = cr.fetchone()
                if res:
                    data['date'] = res[0]
                else:
                    period = period_obj.browse(cr, uid, context['period_id'],
                            context=context)
                    data['date'] = period.date_start

        if not move_id:
            return data

        total = 0
        ref_id = False
        move = self.pool.get('account.move').browse(cr, uid, move_id, context)
        if 'name' in fields:
            data.setdefault('name', move.line_id[-1].name)
        acc1 = False
        for l in move.line_id:
            acc1 = l.account_id
            partner_id = partner_id or l.partner_id.id
            ref_id = ref_id or l.ref
            total += (l.debit or 0.0) - (l.credit or 0.0)

        if 'ref' in fields:
            data['ref'] = ref_id
        if 'partner_id' in fields:
            data['partner_id'] = partner_id

        if move.journal_id.type == 'purchase':
            if total>0:
                account = move.journal_id.default_credit_account_id
            else:
                account = move.journal_id.default_debit_account_id
        else:
            if total>0:
                account = move.journal_id.default_credit_account_id
            else:
                account = move.journal_id.default_debit_account_id

        part = partner_id and self.pool.get('res.partner').browse(cr, uid, partner_id) or False
        # part = False is acceptable for fiscal position.
        account = self.pool.get('account.fiscal.position').map_account(cr, uid, part and part.property_account_position or False, account.id)
        if account:
            account = self.pool.get('account.account').browse(cr, uid, account)

        if account and ((not fields) or ('debit' in fields) or ('credit' in fields)):
            data['account_id'] = account.id
            # Propose the price VAT excluded, the VAT will be added when confirming line
            if account.tax_ids:
                taxes = self.pool.get('account.fiscal.position').map_tax(cr, uid, part and part.property_account_position or False, account.tax_ids)
                tax = self.pool.get('account.tax').browse(cr, uid, taxes)
                for t in self.pool.get('account.tax').compute_inv(cr, uid, tax, total, 1):
                    total -= t['amount']

        s = -total
        data['debit'] = s>0  and s or 0.0
        data['credit'] = s<0  and -s or 0.0

        if account and account.currency_id:
            data['currency_id'] = account.currency_id.id
            acc = account
            if s>0:
                acc = acc1
            v = self.pool.get('res.currency').compute(cr, uid,
                account.company_id.currency_id.id,
                data['currency_id'],
                s, account=acc, account_invert=True)
            data['amount_currency'] = v
        return data

    def _on_create_write(self, cr, uid, id, context={}):
        ml = self.browse(cr, uid, id, context)
        return map(lambda x: x.id, ml.move_id.line_id)

    def _balance(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res={}
        # TODO group the foreach in sql
        for id in ids:
            cr.execute('SELECT date,account_id FROM account_move_line WHERE id=%s', (id,))
            dt, acc = cr.fetchone()
            cr.execute('SELECT SUM(debit-credit) FROM account_move_line WHERE account_id=%s AND (date<%s OR (date=%s AND id<=%s))', (acc,dt,dt,id))
            res[id] = cr.fetchone()[0]
        return res

    def _invoice(self, cursor, user, ids, name, arg, context=None):
        invoice_obj = self.pool.get('account.invoice')
        res = {}
        for line_id in ids:
            res[line_id] = False
        cursor.execute('SELECT l.id, i.id ' \
                       'FROM account_move_line l, account_invoice i ' \
                       'WHERE l.move_id = i.move_id ' \
                       'AND l.id in %s',
                       (tuple(ids),))
        invoice_ids = []
        for line_id, invoice_id in cursor.fetchall():
            res[line_id] = invoice_id
            invoice_ids.append(invoice_id)
        invoice_names = {False: ''}
        for invoice_id, name in invoice_obj.name_get(cursor, user,
                invoice_ids, context=context):
            invoice_names[invoice_id] = name
        for line_id in res.keys():
            invoice_id = res[line_id]
            res[line_id] = (invoice_id, invoice_names[invoice_id])
        return res

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        result = []
        for line in self.browse(cr, uid, ids, context):
            if line.ref:
                result.append((line.id, (line.name or '')+' ('+line.ref+')'))
            else:
                result.append((line.id, line.name))
        return result

    def _invoice_search(self, cursor, user, obj, name, args, context):
        if not len(args):
            return []
        invoice_obj = self.pool.get('account.invoice')

        i = 0
        while i < len(args):
            fargs = args[i][0].split('.', 1)
            if len(fargs) > 1:
                args[i] = (fargs[0], 'in', invoice_obj.search(cursor, user,
                    [(fargs[1], args[i][1], args[i][2])]))
                i += 1
                continue
            if isinstance(args[i][2], basestring):
                res_ids = invoice_obj.name_search(cursor, user, args[i][2], [],
                        args[i][1])
                args[i] = (args[i][0], 'in', [x[0] for x in res_ids])
            i += 1
        qu1, qu2 = [], []
        for x in args:
            if x[1] != 'in':
                if (x[2] is False) and (x[1] == '='):
                    qu1.append('(i.id IS NULL)')
                elif (x[2] is False) and (x[1] == '<>' or x[1] == '!='):
                    qu1.append('(i.id IS NOT NULL)')
                else:
                    qu1.append('(i.id %s %s)' % (x[1], '%s'))
                    qu2.append(x[2])
            elif x[1] == 'in':
                if len(x[2]) > 0:
                    qu1.append('(i.id in (%s))' % (','.join(['%s'] * len(x[2]))))
                    qu2 += x[2]
                else:
                    qu1.append(' (False)')
        if len(qu1):
            qu1 = ' AND' + ' AND'.join(qu1)
        else:
            qu1 = ''
        cursor.execute('SELECT l.id ' \
                'FROM account_move_line l, account_invoice i ' \
                'WHERE l.move_id = i.move_id ' + qu1, qu2)
        res = cursor.fetchall()
        if not len(res):
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    def _get_move_lines(self, cr, uid, ids, context={}):
        result = []
        for move in self.pool.get('account.move').browse(cr, uid, ids, context=context):
            for line in move.line_id:
                result.append(line.id)
        return result

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'quantity': fields.float('Quantity', digits=(16,2), help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very usefull for some reports."),
        'product_uom_id': fields.many2one('product.uom', 'UoM'),
        'product_id': fields.many2one('product.product', 'Product'),
        'debit': fields.float('Debit', digits=(16,2)),
        'credit': fields.float('Credit', digits=(16,2)),
        'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade", domain=[('type','<>','view'), ('type', '<>', 'closed')], select=2),
        'move_id': fields.many2one('account.move', 'Move', ondelete="cascade", states={'valid':[('readonly',True)]}, help="The move of this entry line.", select=2),

        'ref': fields.char('Ref.', size=64),
        'statement_id': fields.many2one('account.bank.statement', 'Statement', help="The bank statement used for bank reconciliation", select=1),
        'reconcile_id': fields.many2one('account.move.reconcile', 'Reconcile', readonly=True, ondelete='set null', select=2),
        'reconcile_partial_id': fields.many2one('account.move.reconcile', 'Partial Reconcile', readonly=True, ondelete='set null', select=2),
        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry."),
        'currency_id': fields.many2one('res.currency', 'Currency', help="The optional other currency if it is a multi-currency entry."),

        'period_id': fields.many2one('account.period', 'Period', required=True, select=2),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, select=1),
        'blocked': fields.boolean('Litigation', help="You can check this box to mark the entry line as a litigation with the associated partner"),

        'partner_id': fields.many2one('res.partner', 'Partner Ref.'),
        'date_maturity': fields.date('Maturity date', help="This field is used for payable and receivable entries. You can put the limit date for the payment of this entry line."),
        'date': fields.related('move_id','date', string='Effective date', type='date', required=True,
            store={
                'account.move': (_get_move_lines, ['date'], 20)
            }),
        'date_created': fields.date('Creation date'),
        'analytic_lines': fields.one2many('account.analytic.line', 'move_id', 'Analytic lines'),
        'centralisation': fields.selection([('normal','Normal'),('credit','Credit Centralisation'),('debit','Debit Centralisation')], 'Centralisation', size=6),
        'balance': fields.function(_balance, method=True, string='Balance'),
        'state': fields.selection([('draft','Draft'), ('valid','Valid')], 'Status', readonly=True),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Account', help="The Account can either be a base tax code or tax code account."),
        'tax_amount': fields.float('Tax/Base Amount', digits=(16,2), select=True, help="If the Tax account is tax code account, this field will contain the taxed amount.If the tax account is base tax code,\
                    this field will contain the basic amount(without tax)."),
        'invoice': fields.function(_invoice, method=True, string='Invoice',
            type='many2one', relation='account.invoice', fnct_search=_invoice_search),
        'account_tax_id':fields.many2one('account.tax', 'Tax'),
        'analytic_account_id' : fields.many2one('account.analytic.account', 'Analytic Account'),
#TODO: remove this
        'amount_taxed':fields.float("Taxed Amount",digits=(16,2)),

    }

    def _get_date(self, cr, uid, context):
        period_obj = self.pool.get('account.period')
        dt = time.strftime('%Y-%m-%d')
        if ('journal_id' in context) and ('period_id' in context):
            cr.execute('select date from account_move_line ' \
                    'where journal_id=%s and period_id=%s ' \
                    'order by id desc limit 1',
                    (context['journal_id'], context['period_id']))
            res = cr.fetchone()
            if res:
                dt = res[0]
            else:
                period = period_obj.browse(cr, uid, context['period_id'],
                        context=context)
                dt = period.date_start
        return dt
    def _get_currency(self, cr, uid, context={}):
        if not context.get('journal_id', False):
            return False
        cur = self.pool.get('account.journal').browse(cr, uid, context['journal_id']).currency
        return cur and cur.id or False

    _defaults = {
        'blocked': lambda *a: False,
        'centralisation': lambda *a: 'normal',
        'date': _get_date,
        'date_created': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'currency_id': _get_currency,
        'journal_id': lambda self, cr, uid, c: c.get('journal_id', False),
        'period_id': lambda self, cr, uid, c: c.get('period_id', False),
    }
    _order = "date desc,id desc"
    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    def _auto_init(self, cr, context={}):
        super(account_move_line, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'account_move_line_journal_id_period_id_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_journal_id_period_id_index ON account_move_line (journal_id, period_id)')
            cr.commit()

    def _check_no_view(self, cr, uid, ids):
        lines = self.browse(cr, uid, ids)
        for l in lines:
            if l.account_id.type == 'view':
                return False
        return True

    def _check_no_closed(self, cr, uid, ids):
        lines = self.browse(cr, uid, ids)
        for l in lines:
            if l.account_id.type == 'closed':
                return False
        return True

    _constraints = [
        (_check_no_view, 'You can not create move line on view account.', ['account_id']),
        (_check_no_closed, 'You can not create move line on closed account.', ['account_id']),
    ]

    #TODO: ONCHANGE_ACCOUNT_ID: set account_tax_id

    def onchange_currency(self, cr, uid, ids, account_id, amount, currency_id, date=False, journal=False):
        if (not currency_id) or (not account_id):
            return {}
        result = {}
        acc =self.pool.get('account.account').browse(cr, uid, account_id)
        if (amount>0) and journal:
            x = self.pool.get('account.journal').browse(cr, uid, journal).default_credit_account_id
            if x: acc = x
        v = self.pool.get('res.currency').compute(cr, uid, currency_id,acc.company_id.currency_id.id, amount, account=acc)
        result['value'] = {
            'debit': v>0 and v or 0.0,
            'credit': v<0 and -v or 0.0
        }
        return result

    def onchange_partner_id(self, cr, uid, ids, move_id, partner_id, account_id=None, debit=0, credit=0, date=False, journal=False):
        val = {}
        val['date_maturity'] = False

        if not partner_id:
            return {'value':val}
        if not date:
            date = now().strftime('%Y-%m-%d')
        part = self.pool.get('res.partner').browse(cr, uid, partner_id)

        if part.property_payment_term:
            res = self.pool.get('account.payment.term').compute(cr, uid, part.property_payment_term.id, 100, date)
            if res:
                val['date_maturity'] = res[0][0]
        if not account_id:
            id1 = part.property_account_payable.id
            id2 =  part.property_account_receivable.id
            if journal:
                jt = self.pool.get('account.journal').browse(cr, uid, journal).type
                if jt == 'sale':
                    val['account_id'] = self.pool.get('account.fiscal.position').map_account(cr, uid, part and part.property_account_position or False, id2)

                elif jt == 'purchase':
                    val['account_id'] = self.pool.get('account.fiscal.position').map_account(cr, uid, part and part.property_account_position or False, id1)
                if val.get('account_id', False):
                    d = self.onchange_account_id(cr, uid, ids, val['account_id'])
                    val.update(d['value'])

        return {'value':val}

    def onchange_account_id(self, cr, uid, ids, account_id=False, partner_id=False):
        val = {}
        if account_id:
            res = self.pool.get('account.account').browse(cr, uid, account_id)
            tax_ids = res.tax_ids
            if tax_ids and partner_id:
                part = self.pool.get('res.partner').browse(cr, uid, partner_id)
                tax_id = self.pool.get('account.fiscal.position').map_tax(cr, uid, part and part.property_account_position or False, tax_ids)[0]
            else:
                tax_id = tax_ids and tax_ids[0].id or False
            val['account_tax_id'] = tax_id
        return {'value':val}

    #
    # type: the type if reconciliation (no logic behind this field, for info)
    #
    # writeoff; entry generated for the difference between the lines
    #

    def reconcile_partial(self, cr, uid, ids, type='auto', context={}):
        merges = []
        unmerge = []
        total = 0.0
        merges_rec = []
        for line in self.browse(cr, uid, ids, context):
            if line.reconcile_id:
                raise osv.except_osv(_('Already Reconciled'), _('Already Reconciled'))
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if not line2.reconcile_id:
                        if line2.id not in merges:
                            merges.append(line2.id)
                        total += (line2.debit or 0.0) - (line2.credit or 0.0)
                merges_rec.append(line.reconcile_partial_id.id)
            else:
                unmerge.append(line.id)
                total += (line.debit or 0.0) - (line.credit or 0.0)

        if not total:
            res = self.reconcile(cr, uid, merges+unmerge, context=context)
            return res
        r_id = self.pool.get('account.move.reconcile').create(cr, uid, {
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerge)
        })
        self.pool.get('account.move.reconcile').reconcile_partial_check(cr, uid, [r_id] + merges_rec, context=context)
        return True

    def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context={}):
        id_set = ','.join(map(str, ids))
        
        lines = self.browse(cr, uid, ids, context=context)
        unrec_lines = filter(lambda x: not x['reconcile_id'], lines)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        invoice = False
        for line in unrec_lines:
            if line.invoice:
                invoice = line.invoice
            if line.state <> 'valid':
                raise osv.except_osv(_('Error'),
                        _('Entry "%s" is not valid !') % line.name)
            credit += line['credit']
            debit += line['debit']
            currency += line['amount_currency'] or 0.0
            account_id = line['account_id']['id']
            account_type = line['account_id']['type']
            partner_id = (line['partner_id'] and line['partner_id']['id']) or False
        writeoff = debit - credit
        # Ifdate_p in context => take this date
        if context.has_key('date_p') and context['date_p']:
            date=context['date_p']
        else:
            date = time.strftime('%Y-%m-%d')

        cr.execute('SELECT account_id, reconcile_id '\
                   'FROM account_move_line '\
                   'WHERE id IN %s '\
                   'GROUP BY account_id,reconcile_id',
                   (tuple(ids),))
        r = cr.fetchall()
#TODO: move this check to a constraint in the account_move_reconcile object
        if (len(r) != 1) and not context.get('fy_closing', False):
            raise osv.except_osv(_('Error'), _('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise osv.except_osv(_('Error'), _('Entry is already reconciled'))
        account = self.pool.get('account.account').browse(cr, uid, account_id, context=context)
        if not context.get('fy_closing', False) and not account.reconcile:
            raise osv.except_osv(_('Error'), _('The account is not defined to be reconciled !'))
        if r[0][1] != None:
            raise osv.except_osv(_('Error'), _('Some entries are already reconciled !'))

        if (not self.pool.get('res.currency').is_zero(cr, uid, account.company_id.currency_id, writeoff)) or \
           (account.currency_id and (not self.pool.get('res.currency').is_zero(cr, uid, account.currency_id, currency))):
            if not writeoff_acc_id:
                raise osv.except_osv(_('Warning'), _('You have to provide an account for the write off entry !'))
            if writeoff > 0:
                debit = writeoff
                credit = 0.0
                self_credit = writeoff
                self_debit = 0.0
            else:
                debit = 0.0
                credit = -writeoff
                self_credit = 0.0
                self_debit = -writeoff

            # If comment exist in context, take it
            if 'comment' in context and context['comment']:
                libelle=context['comment']
            else:
                libelle= _('Write-Off')

            cur_obj = self.pool.get('res.currency')
            cur_id = False
            amount_currency_writeoff = 0.0
            if context.get('company_currency_id',False) != context.get('currency_id',False):
                cur_id = context.get('currency_id',False)
                for line in unrec_lines:
                    #tmp_amount = cur_obj.compute(cr, uid, invoice.company_id.currency_id.id, invoice.currency_id.id, abs(line.debit-line.credit), context={'date': line.date})
                    if line.currency_id and line.currency_id.id == context.get('currency_id',False):
                        amount_currency_writeoff += line.amount_currency
                    else:
                        tmp_amount = cur_obj.compute(cr, uid, line.account_id.company_id.currency_id.id, context.get('currency_id',False), abs(line.debit-line.credit), context={'date': line.date})
                        amount_currency_writeoff += (line.debit > 0) and tmp_amount or -tmp_amount

            writeoff_lines = [
                (0, 0, {
                    'name':libelle,
                    'debit':self_debit,
                    'credit':self_credit,
                    'account_id':account_id,
                    'date':date,
                    'partner_id':partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and -1 * amount_currency_writeoff or (account.currency_id.id and -1 * currency or 0.0)
                }),
                (0, 0, {
                    'name':libelle,
                    'debit':debit,
                    'credit':credit,
                    'account_id':writeoff_acc_id,
                    'analytic_account_id': context.get('analytic_id', False),
                    'date':date,
                    'partner_id':partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and amount_currency_writeoff or (account.currency_id.id and currency or 0.0)
                })
            ]
            writeoff_move_id = self.pool.get('account.move').create(cr, uid, {
                'period_id': writeoff_period_id,
                'journal_id': writeoff_journal_id,
                'date':date,
                'state': 'draft',
                'line_id': writeoff_lines
            })
            writeoff_line_ids = self.search(cr, uid, [('move_id', '=', writeoff_move_id), ('account_id', '=', account_id)])
            if account_id == writeoff_acc_id:
                writeoff_line_ids = [writeoff_line_ids[1]]
            ids += writeoff_line_ids

        r_id = self.pool.get('account.move.reconcile').create(cr, uid, {
            #'name': date,
            'type': type,
            'line_id': map(lambda x: (4,x,False), ids),
            'line_partial_ids': map(lambda x: (3,x,False), ids)
        })
        wf_service = netsvc.LocalService("workflow")
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            wf_service.trg_trigger(uid, 'account.move.line', id, cr)
        return r_id

    def view_header_get(self, cr, user, view_id, view_type, context):
        if context.get('account_id', False):
            cr.execute('select code from account_account where id=%s', (context['account_id'],))
            res = cr.fetchone()
            res = _('Entries: ')+ (res[0] or '')
            return res
        if (not context.get('journal_id', False)) or (not context.get('period_id', False)):
            return False
        cr.execute('select code from account_journal where id=%s', (context['journal_id'],))
        j = cr.fetchone()[0] or ''
        cr.execute('select code from account_period where id=%s', (context['period_id'],))
        p = cr.fetchone()[0] or ''
        if j or p:
            return j+(p and (':'+p) or '')
        return False

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False):
        result = super(osv.osv, self).fields_view_get(cr, uid, view_id,view_type,context,toolbar=toolbar)
        if view_type=='tree' and context.get('journal_id',False):
            title = self.view_header_get(cr, uid, view_id, view_type, context)
            journal = self.pool.get('account.journal').browse(cr, uid, context['journal_id'])

            # if the journal view has a state field, color lines depending on
            # its value
            state = ''
            for field in journal.view_id.columns_id:
                if field.field=='state':
                    state = ' colors="red:state==\'draft\'"'

            #xml = '''<?xml version="1.0"?>\n<tree string="%s" editable="top" refresh="5"%s>\n\t''' % (title, state)
            xml = '''<?xml version="1.0"?>\n<tree string="%s" editable="top" refresh="5" on_write="_on_create_write"%s>\n\t''' % (title, state)
            fields = []

            widths = {
                'ref': 50,
                'statement_id': 50,
                'state': 60,
                'tax_code_id': 50,
                'move_id': 40,
            }
            for field in journal.view_id.columns_id:
                fields.append(field.field)
                attrs = []
                if field.field=='debit':
                    attrs.append('sum="Total debit"')
                elif field.field=='credit':
                    attrs.append('sum="Total credit"')
                elif field.field=='account_tax_id':
                    attrs.append('domain="[(\'parent_id\',\'=\',False)]"')
                elif field.field=='account_id' and journal.id:
                    attrs.append('domain="[(\'journal_id\', \'=\', '+str(journal.id)+'),(\'type\',\'&lt;&gt;\',\'view\'), (\'type\',\'&lt;&gt;\',\'closed\')]" on_change="onchange_account_id(account_id, partner_id)"')
                elif field.field == 'partner_id':
                    attrs.append('on_change="onchange_partner_id(move_id,partner_id,account_id,debit,credit,date,((\'journal_id\' in context) and context[\'journal_id\']) or {})"')
                if field.readonly:
                    attrs.append('readonly="1"')
                if field.required:
                    attrs.append('required="1"')
                else:
                    attrs.append('required="0"')
                if field.field in ('amount_currency','currency_id'):
                    attrs.append('on_change="onchange_currency(account_id,amount_currency,currency_id,date,((\'journal_id\' in context) and context[\'journal_id\']) or {})"')

                if field.field in widths:
                    attrs.append('width="'+str(widths[field.field])+'"')
                xml += '''<field name="%s" %s/>\n''' % (field.field,' '.join(attrs))

            xml += '''</tree>'''
            result['arch'] = xml
            result['fields'] = self.fields_get(cr, uid, fields, context)
        return result
    
    def _check_moves(self, cr, uid, context):
        # use the first move ever created for this journal and period
        cr.execute('select id, state, name from account_move where journal_id=%s and period_id=%s order by id limit 1', (context['journal_id'],context['period_id']))
        res = cr.fetchone()
        if res:
            if res[1] != 'draft':
                raise osv.except_osv(_('UserError'),
                        _('The account move (%s) for centralisation has been confirmed!') % res[2])
        return res

    def unlink(self, cr, uid, ids, context={}, check=True):
        self._update_check(cr, uid, ids, context)
        result = False
        for line in self.browse(cr, uid, ids, context):
            context['journal_id']=line.journal_id.id
            context['period_id']=line.period_id.id
            result = super(account_move_line, self).unlink(cr, uid, [line.id], context=context)
            if check:
                self.pool.get('account.move').validate(cr, uid, [line.move_id.id], context=context)
        return result

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context = {}
        if vals.get('account_tax_id', False):
            raise osv.except_osv(_('Unable to change tax !'), _('You can not change the tax, you should remove and recreate lines !'))

        account_obj = self.pool.get('account.account')
        if ('account_id' in vals) and not account_obj.read(cr, uid, vals['account_id'], ['active'])['active']:
            raise osv.except_osv(_('Bad account!'), _('You can not use an inactive account!'))
        if update_check:
            if ('account_id' in vals) or ('journal_id' in vals) or ('period_id' in vals) or ('move_id' in vals) or ('debit' in vals) or ('credit' in vals) or ('date' in vals):
                self._update_check(cr, uid, ids, context)

        todo_date = None
        if vals.get('date', False):
            todo_date = vals['date']
            del vals['date']

        for line in self.browse(cr, uid, ids,context=context):
            ctx = context.copy()
            if ('journal_id' not in ctx):
                if line.move_id:
                    ctx['journal_id'] = line.move_id.journal_id.id
                else:
                    ctx['journal_id'] = line.journal_id.id
            if ('period_id' not in ctx):
                if line.move_id:
                    ctx['period_id'] = line.move_id.period_id.id
                else:
                    ctx['period_id'] = line.period_id.id  
            #Check for centralisation  
            journal = self.pool.get('account.journal').browse(cr, uid, ctx['journal_id'], context=ctx)
            if journal.centralisation:
                self._check_moves(cr, uid, context=ctx)

        
        result = super(account_move_line, self).write(cr, uid, ids, vals, context)

        if check:
            done = []
            for line in self.browse(cr, uid, ids):
                if line.move_id.id not in done:
                    done.append(line.move_id.id)
                    self.pool.get('account.move').validate(cr, uid, [line.move_id.id], context)
                    if todo_date:
                        self.pool.get('account.move').write(cr, uid, [line.move_id.id], {'date': todo_date}, context=context)
        return result

    def _update_journal_check(self, cr, uid, journal_id, period_id, context={}):
        cr.execute('select state from account_journal_period where journal_id=%s and period_id=%s', (journal_id, period_id))
        result = cr.fetchall()
        for (state,) in result:
            if state=='done':
                raise osv.except_osv(_('Error !'), _('You can not add/modify entries in a closed journal.'))
        if not result:
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context)
            period = self.pool.get('account.period').browse(cr, uid, period_id, context)
            self.pool.get('account.journal.period').create(cr, uid, {
                'name': (journal.code or journal.name)+':'+(period.name or ''),
                'journal_id': journal.id,
                'period_id': period.id
            })
        return True

    def _update_check(self, cr, uid, ids, context={}):
        done = {}
        for line in self.browse(cr, uid, ids, context):
            if line.move_id.state<>'draft' and (not line.journal_id.entry_posted):
                raise osv.except_osv(_('Error !'), _('You can not do this modification on a confirmed entry ! Please note that you can just change some non important fields !'))
            if line.reconcile_id:
                raise osv.except_osv(_('Error !'), _('You can not do this modification on a reconciled entry ! Please note that you can just change some non important fields !'))
            t = (line.journal_id.id, line.period_id.id)
            if t not in done:
                self._update_journal_check(cr, uid, line.journal_id.id, line.period_id.id, context)
                done[t] = True
        return True

    def create(self, cr, uid, vals, context=None, check=True):
        if not context:
            context={}
        account_obj = self.pool.get('account.account')
        tax_obj=self.pool.get('account.tax')
        if ('account_id' in vals) and not account_obj.read(cr, uid, vals['account_id'], ['active'])['active']:
            raise osv.except_osv(_('Bad account!'), _('You can not use an inactive account!'))
        if 'journal_id' in vals and 'journal_id' not in context:
            context['journal_id'] = vals['journal_id']
        if 'period_id' in vals and 'period_id' not in context:
            context['period_id'] = vals['period_id']
        if ('journal_id' not in context) and ('move_id' in vals) and vals['move_id']:
            m = self.pool.get('account.move').browse(cr, uid, vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['period_id'] = m.period_id.id

        self._update_journal_check(cr, uid, context['journal_id'], context['period_id'], context)
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id

        move_id = vals.get('move_id', False)
        journal = self.pool.get('account.journal').browse(cr, uid, context['journal_id'])
        is_new_move = False
        if not move_id:
            if journal.centralisation:
                #Check for centralisation
                res = self._check_moves(cr, uid, context)
                if res:
                    vals['move_id'] = res[0]

            if not vals.get('move_id', False):
                if journal.sequence_id:
                    #name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id)
                    v = {
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'period_id': context['period_id'],
                        'journal_id': context['journal_id']
                    }
                    move_id = self.pool.get('account.move').create(cr, uid, v, context)
                    vals['move_id'] = move_id
                else:
                    raise osv.except_osv(_('No piece number !'), _('Can not create an automatic sequence for this piece !\n\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.'))
            is_new_move = True

        ok = not (journal.type_control_ids or journal.account_control_ids)
        if ('account_id' in vals):
            account = account_obj.browse(cr, uid, vals['account_id'])
            if journal.type_control_ids:
                type = account.user_type
                for t in journal.type_control_ids:
                    if type.code == t.code:
                        ok = True
                        break
            if journal.account_control_ids and not ok:
                for a in journal.account_control_ids:
                    if a.id==vals['account_id']:
                        ok = True
                        break
            if (account.currency_id) and 'amount_currency' not in vals and account.currency_id.id <> company_currency:
                vals['currency_id'] = account.currency_id.id
                cur_obj = self.pool.get('res.currency')
                ctx = {}
                if 'date' in vals:
                    ctx['date'] = vals['date']
                vals['amount_currency'] = cur_obj.compute(cr, uid, account.company_id.currency_id.id,
                    account.currency_id.id, vals.get('debit', 0.0)-vals.get('credit', 0.0),
                    context=ctx)
        if not ok:
            raise osv.except_osv(_('Bad account !'), _('You can not use this general account in this journal !'))

        if vals.get('analytic_account_id',False):
            if journal.analytic_journal_id:
                vals['analytic_lines'] = [(0,0, {
                        'name': vals['name'],
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'account_id': vals['analytic_account_id'],
                        'unit_amount': vals.get('quantity',1.0),
                        'amount': vals.get('debit',0.0) or vals.get('credit',0.0),
                        'general_account_id': vals['account_id'],
                        'journal_id': journal.analytic_journal_id.id,
                        'ref': vals.get('ref', False),
                    })]
            #else:
            #    raise osv.except_osv(_('No analytic journal !'), _('Please set an analytic journal on this financial journal !'))

        #if not 'currency_id' in vals:
        #    vals['currency_id'] = account.company_id.currency_id.id

        result = super(osv.osv, self).create(cr, uid, vals, context)
        # CREATE Taxes
        if 'account_tax_id' in vals and vals['account_tax_id']:
            tax_id=tax_obj.browse(cr,uid,vals['account_tax_id'])
            total = vals['debit'] - vals['credit']
            if journal.refund_journal:
                base_code = 'ref_base_code_id'
                tax_code = 'ref_tax_code_id'
                account_id = 'account_paid_id'
                base_sign = 'ref_base_sign'
                tax_sign = 'ref_tax_sign'
            else:
                base_code = 'base_code_id'
                tax_code = 'tax_code_id'
                account_id = 'account_collected_id'
                base_sign = 'base_sign'
                tax_sign = 'tax_sign'

            tmp_cnt = 0
            for tax in tax_obj.compute(cr,uid,[tax_id],total,1.00):
                #create the base movement
                if tmp_cnt == 0:
                    if tax[base_code]:
                        tmp_cnt += 1
                        self.write(cr, uid,[result], {
                            'tax_code_id': tax[base_code],
                            'tax_amount': tax[base_sign] * abs(total)
                        })
                else:
                    data = {
                        'move_id': vals['move_id'],
                        'journal_id': vals['journal_id'],
                        'period_id': vals['period_id'],
                        'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                        'date': vals['date'],
                        'partner_id': vals.get('partner_id',False),
                        'ref': vals.get('ref',False),
                        'account_tax_id': False,
                        'tax_code_id': tax[base_code],
                        'tax_amount': tax[base_sign] * abs(total),
                        'account_id': vals['account_id'],
                        'credit': 0.0,
                        'debit': 0.0,
                    }
                    if data['tax_code_id']:
                        self.create(cr, uid, data, context)

                #create the VAT movement
                data = {
                    'move_id': vals['move_id'],
                    'journal_id': vals['journal_id'],
                    'period_id': vals['period_id'],
                    'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                    'date': vals['date'],
                    'partner_id': vals.get('partner_id',False),
                    'ref': vals.get('ref',False),
                    'account_tax_id': False,
                    'tax_code_id': tax[tax_code],
                    'tax_amount': tax[tax_sign] * abs(tax['amount']),
                    'account_id': tax[account_id] or vals['account_id'],
                    'credit': tax['amount']<0 and -tax['amount'] or 0.0,
                    'debit': tax['amount']>0 and tax['amount'] or 0.0,
                }
                if data['tax_code_id']:
                    self.create(cr, uid, data, context)
            del vals['account_tax_id']

        # No needed, related to the job
        #if not is_new_move and 'date' in vals:
        #    if context and ('__last_update' in context):
        #        del context['__last_update']
        #    self.pool.get('account.move').write(cr, uid, [move_id], {'date':vals['date']}, context=context)
        if check and ((not context.get('no_store_function')) or journal.entry_posted):
            tmp = self.pool.get('account.move').validate(cr, uid, [vals['move_id']], context)
            if journal.entry_posted and tmp:
                self.pool.get('account.move').button_validate(cr,uid, [vals['move_id']],context)
        return result
account_move_line()


class account_bank_statement_reconcile(osv.osv):
    _inherit = "account.bank.statement.reconcile"
    _columns = {
        'line_ids': fields.many2many('account.move.line', 'account_bank_statement_line_rel', 'statement_id', 'line_id', 'Entries'),
    }
account_bank_statement_reconcile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

