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

from operator import itemgetter
import time

from openerp.osv import fields, osv

class account_fiscal_position(osv.osv):
    _name = 'account.fiscal.position'
    _description = 'Fiscal Position'
    _columns = {
        'name': fields.char('Fiscal Position', size=64, required=True),
        'active': fields.boolean('Active', help="By unchecking the active field, you may hide a fiscal position without deleting it."),
        'company_id': fields.many2one('res.company', 'Company'),
        'account_ids': fields.one2many('account.fiscal.position.account', 'position_id', 'Account Mapping'),
        'tax_ids': fields.one2many('account.fiscal.position.tax', 'position_id', 'Tax Mapping'),
        'note': fields.text('Notes'),
    }

    _defaults = {
        'active': True,
    }

    def map_tax(self, cr, uid, fposition_id, taxes, context=None):
        if not taxes:
            return []
        if not fposition_id:
            return map(lambda x: x.id, taxes)
        result = set()
        for t in taxes:
            ok = False
            for tax in fposition_id.tax_ids:
                if tax.tax_src_id.id == t.id:
                    if tax.tax_dest_id:
                        result.add(tax.tax_dest_id.id)
                    ok=True
            if not ok:
                result.add(t.id)
        return list(result)

    def map_account(self, cr, uid, fposition_id, account_id, context=None):
        if not fposition_id:
            return account_id
        for pos in fposition_id.account_ids:
            if pos.account_src_id.id == account_id:
                account_id = pos.account_dest_id.id
                break
        return account_id


class account_fiscal_position_tax(osv.osv):
    _name = 'account.fiscal.position.tax'
    _description = 'Taxes Fiscal Position'
    _rec_name = 'position_id'
    _columns = {
        'position_id': fields.many2one('account.fiscal.position', 'Fiscal Position', required=True, ondelete='cascade'),
        'tax_src_id': fields.many2one('account.tax', 'Tax Source', required=True),
        'tax_dest_id': fields.many2one('account.tax', 'Replacement Tax')
    }

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id,tax_dest_id)',
         'A tax fiscal position could be defined only once time on same taxes.')
    ]


class account_fiscal_position_account(osv.osv):
    _name = 'account.fiscal.position.account'
    _description = 'Accounts Fiscal Position'
    _rec_name = 'position_id'
    _columns = {
        'position_id': fields.many2one('account.fiscal.position', 'Fiscal Position', required=True, ondelete='cascade'),
        'account_src_id': fields.many2one('account.account', 'Account Source', domain=[('type','<>','view')], required=True),
        'account_dest_id': fields.many2one('account.account', 'Account Destination', domain=[('type','<>','view')], required=True)
    }

    _sql_constraints = [
        ('account_src_dest_uniq',
         'unique (position_id,account_src_id,account_dest_id)',
         'An account fiscal position could be defined only once time on same accounts.')
    ]


class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Partner'

    def _credit_debit_get(self, cr, uid, ids, field_names, arg, context=None):
        ctx = context.copy()
        ctx['all_fiscalyear'] = True
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=ctx)
        cr.execute("""SELECT l.partner_id, a.type, SUM(l.debit-l.credit)
                      FROM account_move_line l
                      LEFT JOIN account_account a ON (l.account_id=a.id)
                      WHERE a.type IN ('receivable','payable')
                      AND l.partner_id IN %s
                      AND l.reconcile_id IS NULL
                      AND """ + query + """
                      GROUP BY l.partner_id, a.type
                      """,
                   (tuple(ids),))
        maps = {'receivable':'credit', 'payable':'debit' }
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0)
        for pid,type,val in cr.fetchall():
            if val is None: val=0
            res[pid][maps[type]] = (type=='receivable') and val or -val
        return res

    def _asset_difference_search(self, cr, uid, obj, name, type, args, context=None):
        if not args:
            return []
        having_values = tuple(map(itemgetter(2), args))
        where = ' AND '.join(
            map(lambda x: '(SUM(bal2) %(operator)s %%s)' % {
                                'operator':x[1]},args))
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute(('SELECT pid AS partner_id, SUM(bal2) FROM ' \
                    '(SELECT CASE WHEN bal IS NOT NULL THEN bal ' \
                    'ELSE 0.0 END AS bal2, p.id as pid FROM ' \
                    '(SELECT (debit-credit) AS bal, partner_id ' \
                    'FROM account_move_line l ' \
                    'WHERE account_id IN ' \
                            '(SELECT id FROM account_account '\
                            'WHERE type=%s AND active) ' \
                    'AND reconcile_id IS NULL ' \
                    'AND '+query+') AS l ' \
                    'RIGHT JOIN res_partner p ' \
                    'ON p.id = partner_id ) AS pl ' \
                    'GROUP BY pid HAVING ' + where), 
                    (type,) + having_values)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in',map(itemgetter(0), res))]

    def _credit_search(self, cr, uid, obj, name, args, context=None):
        return self._asset_difference_search(cr, uid, obj, name, 'receivable', args, context=context)

    def _debit_search(self, cr, uid, obj, name, args, context=None):
        return self._asset_difference_search(cr, uid, obj, name, 'payable', args, context=context)

    def _invoice_total(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        account_invoice_report = self.pool.get('account.invoice.report')
        for partner in self.browse(cr, uid, ids, context=context):
            invoice_ids = account_invoice_report.search(cr, uid, [('partner_id','child_of',partner.id)], context=context)
            invoices = account_invoice_report.browse(cr, uid, invoice_ids, context=context)
            result[partner.id] = sum(inv.user_currency_price_total for inv in invoices)
        return result

    def _journal_item_count(self, cr, uid, ids, field_name, arg, context=None):
        MoveLine = self.pool('account.move.line')
        AnalyticAccount = self.pool('account.analytic.account')
        return {
            partner_id: {
                'journal_item_count': MoveLine.search_count(cr, uid, [('partner_id', '=', partner_id)], context=context),
                'contracts_count': AnalyticAccount.search_count(cr,uid, [('partner_id', '=', partner_id)], context=context)
            }
            for partner_id in ids
        }

    def has_something_to_reconcile(self, cr, uid, partner_id, context=None):
        '''
        at least a debit, a credit and a line older than the last reconciliation date of the partner
        '''
        cr.execute('''
            SELECT l.partner_id, SUM(l.debit) AS debit, SUM(l.credit) AS credit
            FROM account_move_line l
            RIGHT JOIN account_account a ON (a.id = l.account_id)
            RIGHT JOIN res_partner p ON (l.partner_id = p.id)
            WHERE a.reconcile IS TRUE
            AND p.id = %s
            AND l.reconcile_id IS NULL
            AND (p.last_reconciliation_date IS NULL OR l.date > p.last_reconciliation_date)
            AND l.state <> 'draft'
            GROUP BY l.partner_id''', (partner_id,))
        res = cr.dictfetchone()
        if res:
            return bool(res['debit'] and res['credit'])
        return False

    def mark_as_reconciled(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'last_reconciliation_date': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)

    _columns = {
        'credit': fields.function(_credit_debit_get,
            fnct_search=_credit_search, string='Total Receivable', multi='dc', help="Total amount this customer owes you."),
        'debit': fields.function(_credit_debit_get, fnct_search=_debit_search, string='Total Payable', multi='dc', help="Total amount you have to pay to this supplier."),
        'debit_limit': fields.float('Payable Limit'),
        'total_invoiced': fields.function(_invoice_total, string="Total Invoiced", type='float'),
        'contracts_count': fields.function(_journal_item_count, string="Contracts", type='integer', multi="invoice_journal"),
        'journal_item_count': fields.function(_journal_item_count, string="Journal Items", type="integer", multi="invoice_journal"),
        'property_account_payable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Payable",
            domain="[('type', '=', 'payable')]",
            help="This account will be used instead of the default one as the payable account for the current partner",
            required=True),
        'property_account_receivable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as the receivable account for the current partner",
            required=True),
        'property_account_position': fields.property(
            type='many2one',
            relation='account.fiscal.position',
            string="Fiscal Position",
            help="The fiscal position will determine taxes and accounts used for the partner.",
        ),
        'property_payment_term': fields.property(
            type='many2one',
            relation='account.payment.term',
            string ='Customer Payment Term',
            help="This payment term will be used instead of the default one for sale orders and customer invoices"),
        'property_supplier_payment_term': fields.property(
             type='many2one',
             relation='account.payment.term',
             string ='Supplier Payment Term',
             help="This payment term will be used instead of the default one for purchase orders and supplier invoices"),
        'ref_companies': fields.one2many('res.company', 'partner_id',
            'Companies that refers to partner'),
        'last_reconciliation_date': fields.datetime('Latest Full Reconciliation Date', help='Date on which the partner accounting entries were fully reconciled last time. It differs from the last date where a reconciliation has been made for this partner, as here we depict the fact that nothing more was to be reconciled at this date. This can be achieved in 2 different ways: either the last unreconciled debit/credit entry of this partner was reconciled, either the user pressed the button "Nothing more to reconcile" during the manual reconciliation process.')
    }

    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + \
            ['debit_limit', 'property_account_payable', 'property_account_receivable', 'property_account_position',
             'property_payment_term', 'property_supplier_payment_term', 'last_reconciliation_date']


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
