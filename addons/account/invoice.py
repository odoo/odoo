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
from operator import itemgetter

import netsvc
from osv import fields, osv
from osv.orm import except_orm
import pooler
from tools import config
from tools.translate import _

class fiscalyear_seq(osv.osv):
    _name = "fiscalyear.seq"
    _description = "Maintains Invoice sequences with Fiscal Year"
    _rec_name = 'fiscalyear_id'
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year',required=True),
        'sequence_id':fields.many2one('ir.sequence', 'Sequence',required=True),
    }

fiscalyear_seq()

class account_invoice(osv.osv):
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr,uid,ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                res[invoice.id]['amount_tax'] += line.amount
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']
        return res

    def _get_journal(self, cr, uid, context):
        if context is None:
            context = {}
        type_inv = context.get('type', 'out_invoice')
        type2journal = {'out_invoice': 'sale', 'in_invoice': 'purchase', 'out_refund': 'sale', 'in_refund': 'purchase'}
        refund_journal = {'out_invoice': False, 'in_invoice': False, 'out_refund': True, 'in_refund': True}
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('type', '=', type2journal.get(type_inv, 'sale')), ('refund_journal', '=', refund_journal.get(type_inv, False))], limit=1)
        if res:
            return res[0]
        else:
            return False

    def _get_currency(self, cr, uid, context):
        user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, [uid])[0]
        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return pooler.get_pool(cr.dbname).get('res.currency').search(cr, uid, [('rate','=',1.0)])[0]

    def _get_journal_analytic(self, cr, uid, type_inv, context=None):
        type2journal = {'out_invoice': 'sale', 'in_invoice': 'purchase', 'out_refund': 'sale', 'in_refund': 'purchase'}
        tt = type2journal.get(type_inv, 'sale')
        result = self.pool.get('account.analytic.journal').search(cr, uid, [('type','=',tt)], context=context)
        if not result:
            raise osv.except_osv(_('No Analytic Journal !'),_("You must define an analytic journal of type '%s' !") % (tt,))
        return result[0]

    def _get_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        type = context.get('type', 'out_invoice')
        return type

    def _reconciled(self, cr, uid, ids, name, args, context):
        res = {}
        for id in ids:
            res[id] = self.test_paid(cr, uid, [id])
        return res

    def _get_reference_type(self, cr, uid, context=None):
        return [('none', _('Free Reference'))]

    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        data_inv = self.browse(cr, uid, ids)
        cur_obj = self.pool.get('res.currency')
        for inv in data_inv:
            if inv.reconciled: 
                res[inv.id] = 0.0
                continue
            inv_total = inv.amount_total
            context_unreconciled = context.copy()
            for lines in inv.move_lines:
                if lines.currency_id and lines.currency_id.id == inv.currency_id.id:
                   if inv.type in ('out_invoice','in_refund'):
                        inv_total += lines.amount_currency
                   else:
                        inv_total -= lines.amount_currency
                else:
                   context_unreconciled.update({'date': lines.date})
                   amount_in_invoice_currency = cur_obj.compute(cr, uid, inv.company_id.currency_id.id, inv.currency_id.id,abs(lines.debit-lines.credit),round=False,context=context_unreconciled)
                   inv_total -= amount_in_invoice_currency

            result = inv_total 
            res[inv.id] =  self.pool.get('res.currency').round(cr, uid, inv.currency_id, result)
        return res

    def _get_lines(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for id in ids:
            move_lines = self.move_line_id_payment_get(cr,uid,[id])
            if not move_lines:
                res[id] = []
                continue
            res[id] = []
            data_lines = self.pool.get('account.move.line').browse(cr,uid,move_lines)
            partial_ids = []# Keeps the track of ids where partial payments are done with payment terms
            for line in data_lines:
                ids_line = []
                if line.reconcile_id:
                    ids_line = line.reconcile_id.line_id
                elif line.reconcile_partial_id:
                    ids_line = line.reconcile_partial_id.line_partial_ids
                l = map(lambda x: x.id, ids_line)
                partial_ids.append(line.id)
                res[id] =[x for x in l if x <> line.id and x not in partial_ids]
        return res

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    def _compute_lines(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context):
            moves = self.move_line_id_payment_get(cr, uid, [invoice.id])
            src = []
            lines = []
            for m in self.pool.get('account.move.line').browse(cr, uid, moves, context):
                temp_lines = []#Added temp list to avoid duplicate records
                if m.reconcile_id:
                    temp_lines = map(lambda x: x.id, m.reconcile_id.line_id)
                elif m.reconcile_partial_id:
                    temp_lines = map(lambda x: x.id, m.reconcile_partial_id.line_partial_ids)
                lines += [x for x in temp_lines if x not in lines]
                src.append(m.id)
            lines = filter(lambda x: x not in src, lines)
            result[invoice.id] = lines
        return result

    def _get_invoice_from_line(self, cr, uid, ids, context={}):
        move = {}
        for line in self.pool.get('account.move.line').browse(cr, uid, ids):
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    move[line2.move_id.id] = True
            if line.reconcile_id:
                for line2 in line.reconcile_id.line_id:
                    move[line2.move_id.id] = True
        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids

    def _get_invoice_from_reconcile(self, cr, uid, ids, context={}):
        move = {}
        for r in self.pool.get('account.move.reconcile').browse(cr, uid, ids):
            for line in r.line_partial_ids:
                move[line.move_id.id] = True
            for line in r.line_id:
                move[line.move_id.id] = True
        
        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids

    _name = "account.invoice"
    _description = 'Invoice'
    _order = "number"
    _columns = {
        'name': fields.char('Description', size=64, select=True,readonly=True, states={'draft':[('readonly',False)]}),
        'origin': fields.char('Origin', size=64, help="Reference of the document that produced this invoice."),
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ],'Type', readonly=True, select=True),

        'number': fields.char('Invoice Number', size=32, readonly=True, help="Unique number of the invoice, computed automatically when the invoice is created."),
        'reference': fields.char('Invoice Reference', size=64, help="The partner reference of this invoice."),
        'reference_type': fields.selection(_get_reference_type, 'Reference Type',
            required=True),
        'comment': fields.text('Additional Information'),

        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('paid','Done'),
            ('cancel','Cancelled')
        ],'State', select=True, readonly=True),

        'date_invoice': fields.date('Date Invoiced', states={'open':[('readonly',True)],'close':[('readonly',True)]}, help="Keep empty to use the current date"),
        'date_due': fields.date('Due Date', states={'open':[('readonly',True)],'close':[('readonly',True)]},
            help="If you use payment terms, the due date will be computed automatically at the generation "\
                "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. The payment term may compute several due dates, for example 50% now, 50% in one month."),
        'partner_id': fields.many2one('res.partner', 'Partner', change_default=True, readonly=True, required=True, states={'draft':[('readonly',False)]}),
        'address_contact_id': fields.many2one('res.partner.address', 'Contact Address', readonly=True, states={'draft':[('readonly',False)]}),
        'address_invoice_id': fields.many2one('res.partner.address', 'Invoice Address', readonly=True, required=True, states={'draft':[('readonly',False)]}),
        'payment_term': fields.many2one('account.payment.term', 'Payment Term',readonly=True, states={'draft':[('readonly',False)]},
            help="If you use payment terms, the due date will be computed automatically at the generation "\
                "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. "\
                "The payment term may compute several due dates, for example 50% now, 50% in one month."),
        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')], help="Keep empty to use the period of the validation(invoice) date.", readonly=True, states={'draft':[('readonly',False)]}),

        'account_id': fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="The partner account used for this invoice."),
        'invoice_line': fields.one2many('account.invoice.line', 'invoice_id', 'Invoice Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'tax_line': fields.one2many('account.invoice.tax', 'invoice_id', 'Tax Lines', readonly=True, states={'draft':[('readonly',False)]}),

        'move_id': fields.many2one('account.move', 'Invoice Movement', readonly=True, help="Link to the automatically generated account moves."),
        'amount_untaxed': fields.function(_amount_all, method=True, digits=(16, int(config['price_accuracy'])),string='Untaxed',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'amount_tax': fields.function(_amount_all, method=True, digits=(16, int(config['price_accuracy'])), string='Tax',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'amount_total': fields.function(_amount_all, method=True, digits=(16, int(config['price_accuracy'])), string='Total',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'check_total': fields.float('Total', digits=(16, int(config['price_accuracy'])), states={'open':[('readonly',True)],'close':[('readonly',True)]}),
        'reconciled': fields.function(_reconciled, method=True, string='Paid/Reconciled', type='boolean',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, None, 50), # Check if we can remove ?
                'account.move.line': (_get_invoice_from_line, None, 50),
                'account.move.reconcile': (_get_invoice_from_reconcile, None, 50),
            }, help="The account moves of the invoice have been reconciled with account moves of the payment(s)."),
        'partner_bank': fields.many2one('res.partner.bank', 'Bank Account',
            help='The bank account to pay to or to be paid from'),
        'move_lines':fields.function(_get_lines , method=True,type='many2many' , relation='account.move.line',string='Move Lines'),
        'residual': fields.function(_amount_residual, method=True, digits=(16, int(config['price_accuracy'])),string='Residual',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 50),
                'account.invoice.tax': (_get_invoice_tax, None, 50),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 50),
                'account.move.line': (_get_invoice_from_line, None, 50),
                'account.move.reconcile': (_get_invoice_from_reconcile, None, 50),
            },
            help="Remaining amount due."),
        'payment_ids': fields.function(_compute_lines, method=True, relation='account.move.line', type="many2many", string='Payments'),
        'move_name': fields.char('Account Move', size=64),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position')
    }
    _defaults = {
        'type': _get_type,
        #'date_invoice': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'journal_id': _get_journal,
        'currency_id': _get_currency,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'reference_type': lambda *a: 'none',
        'check_total': lambda *a: 0.0,
    }
    
    def create(self, cr, uid, vals, context={}):
        try:
            res = super(account_invoice, self).create(cr, uid, vals, context)
            return res
        except Exception,e:
            if '"journal_id" viol' in e.args[0]:
                raise except_orm(_('Configuration Error!'),
                     _('There is no Accounting Journal of type Sale/Purchase defined!'))
            else:
                raise except_orm(_('UnknownError'), str(e))
            
    def unlink(self, cr, uid, ids, context=None):
        invoices = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for t in invoices:
            if t['state'] in ('draft', 'cancel'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete invoice(s) that are already opened or paid !'))
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True

#   def get_invoice_address(self, cr, uid, ids):
#       res = self.pool.get('res.partner').address_get(cr, uid, [part], ['invoice'])
#       return [{}]

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,
            date_invoice=False, payment_term=False, partner_bank=False):
        invoice_addr_id = False
        contact_addr_id = False
        partner_payment_term = False
        acc_id = False
        bank_id = False
        fiscal_position = False

        opt = [('uid', str(uid))]
        if partner_id:

            opt.insert(0, ('id', partner_id))
            res = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['contact', 'invoice'])
            contact_addr_id = res['contact']
            invoice_addr_id = res['invoice']
            p = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if type in ('out_invoice', 'out_refund'):
                acc_id = p.property_account_receivable.id
            else:
                acc_id = p.property_account_payable.id
            fiscal_position = p.property_account_position and p.property_account_position.id or False
            partner_payment_term = p.property_payment_term and p.property_payment_term.id or False
            if p.bank_ids:
                bank_id = p.bank_ids[0].id

        result = {'value': {
            'address_contact_id': contact_addr_id,
            'address_invoice_id': invoice_addr_id,
            'account_id': acc_id,
            'payment_term': partner_payment_term,
            'fiscal_position': fiscal_position
            }
        }

        if type in ('in_invoice', 'in_refund'):
            result['value']['partner_bank'] = bank_id

        if partner_bank != bank_id:
            to_update = self.onchange_partner_bank(cr, uid, ids, bank_id)
            result['value'].update(to_update['value'])
        return result

    def onchange_currency_id(self, cr, uid, ids, curr_id):
        return {}

    def onchange_payment_term_date_invoice(self, cr, uid, ids, payment_term_id, date_invoice):
        if not payment_term_id:
            return {}
        res={}
        pt_obj= self.pool.get('account.payment.term')
        if not date_invoice :
            date_invoice = time.strftime('%Y-%m-%d')

        pterm_list = pt_obj.compute(cr, uid, payment_term_id, value=1, date_ref=date_invoice)

        if pterm_list:
            pterm_list = [line[0] for line in pterm_list]
            pterm_list.sort()
            res= {'value':{'date_due': pterm_list[-1]}}
        else:
             raise osv.except_osv(_('Data Insufficient !'), _('The Payment Term of Supplier does not have Payment Term Lines(Computation) defined !'))

        return res

    def onchange_invoice_line(self, cr, uid, ids, lines):
        return {}

    def onchange_partner_bank(self, cursor, user, ids, partner_bank):
        return {'value': {}}

    # go from canceled state to draft state
    def action_cancel_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'draft'})
        wf_service = netsvc.LocalService("workflow")
        for inv_id in ids:
            wf_service.trg_create(uid, 'account.invoice', inv_id, cr)
        return True

    # Workflow stuff
    #################

    # return the ids of the move lines which has the same account than the invoice
    # whose id is in ids
    def move_line_id_payment_get(self, cr, uid, ids, *args):
        res = []
        if not ids: return res
        cr.execute('SELECT l.id '\
                   'FROM account_move_line l '\
                   'LEFT JOIN account_invoice i ON (i.move_id=l.move_id) '\
                   'WHERE i.id IN %s '\
                   'AND l.account_id=i.account_id',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'state':'draft', 'number':False, 'move_id':False, 'move_name':False,})
        if 'date_invoice' not in default:
            default['date_invoice'] = False
        if 'date_due' not in default:
            default['date_due'] = False
        return super(account_invoice, self).copy(cr, uid, id, default, context)

    def test_paid(self, cr, uid, ids, *args):
        res = self.move_line_id_payment_get(cr, uid, ids)
        if not res:
            return False
        ok = True
        for id in res:
            cr.execute('select reconcile_id from account_move_line where id=%s', (id,))
            ok = ok and  bool(cr.fetchone()[0])
        return ok

    def button_reset_taxes(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        ctx = context.copy()
        ait_obj = self.pool.get('account.invoice.tax')
        for id in ids:
            cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s", (id,))
            partner = self.browse(cr, uid, id,context=ctx).partner_id
            if partner.lang:
                ctx.update({'lang': partner.lang})
            for taxe in ait_obj.compute(cr, uid, id, context=ctx).values():
                ait_obj.create(cr, uid, taxe)
         # Update the stored value (fields.function), so we write to trigger recompute
        self.pool.get('account.invoice').write(cr, uid, ids, {'invoice_line':[]}, context=ctx)    
#        self.pool.get('account.invoice').write(cr, uid, ids, {}, context=context)
        return True

    def button_compute(self, cr, uid, ids, context=None, set_total=False):
        self.button_reset_taxes(cr, uid, ids, context)
        for inv in self.browse(cr, uid, ids):
            if set_total:
                self.pool.get('account.invoice').write(cr, uid, [inv.id], {'check_total': inv.amount_total})
        return True

    def _convert_ref(self, cr, uid, ref):
        return (ref or '').replace('/','')

    def _get_analytic_lines(self, cr, uid, id):
        inv = self.browse(cr, uid, [id])[0]
        cur_obj = self.pool.get('res.currency')

        company_currency = inv.company_id.currency_id.id
        if inv.type in ('out_invoice', 'in_refund'):
            sign = 1
        else:
            sign = -1

        iml = self.pool.get('account.invoice.line').move_line_get(cr, uid, inv.id)
        for il in iml:
            if il['account_analytic_id']:
                if inv.type in ('in_invoice', 'in_refund'):
                    ref = inv.reference
                else:
                    ref = self._convert_ref(cr, uid, inv.number)
                il['analytic_lines'] = [(0,0, {
                    'name': il['name'],
                    'date': inv['date_invoice'],
                    'account_id': il['account_analytic_id'],
                    'unit_amount': il['quantity'],
                    'amount': cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, il['price'], context={'date': inv.date_invoice}) * sign,
                    'product_id': il['product_id'],
                    'product_uom_id': il['uos_id'],
                    'general_account_id': il['account_id'],
                    'journal_id': self._get_journal_analytic(cr, uid, inv.type),
                    'ref': ref,
                })]
        return iml

    def action_date_assign(self, cr, uid, ids, *args):
        for inv in self.browse(cr, uid, ids):
            res = self.onchange_payment_term_date_invoice(cr, uid, inv.id, inv.payment_term.id, inv.date_invoice)
            if res and res['value']:
                self.write(cr, uid, [inv.id], res['value'])
        return True
    
    def finalize_invoice_move_lines(self, cr, uid, invoice_browse, move_lines):
        """finalize_invoice_move_lines(cr, uid, invoice, move_lines) -> move_lines
        Hook method to be overridden in additional modules to verify and possibly alter the 
        move lines to be created by an invoice, for special cases.
        :param invoice_browse: browsable record of the invoice that is generating the move lines
        :param move_lines: list of dictionaries with the account.move.lines (as for create())
        :return: the (possibly updated) final move_lines to create for this invoice 
        """
        return move_lines

    def action_move_create(self, cr, uid, ids, *args):
        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        context = {}
        for inv in self.browse(cr, uid, ids):
            if inv.move_id:
                continue

            if not inv.date_invoice:
                self.write(cr, uid, [inv.id], {'date_invoice':time.strftime('%Y-%m-%d')})
            company_currency = inv.company_id.currency_id.id
            # create the analytical lines
            line_ids = self.read(cr, uid, [inv.id], ['invoice_line'])[0]['invoice_line']
            # one move line per invoice line
            iml = self._get_analytic_lines(cr, uid, inv.id)
            # check if taxes are all computed
            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})
            compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
            if not inv.tax_line:
                for tax in compute_taxes.values():
                    ait_obj.create(cr, uid, tax)
            else:
                tax_key = []
                for tax in inv.tax_line:
                    if tax.manual:
                        continue
                    key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
                    tax_key.append(key)
                    if not key in compute_taxes:
                        raise osv.except_osv(_('Warning !'), _('Global taxes defined, but are not in invoice lines !'))
                    base = compute_taxes[key]['base']
                    if abs(base - tax.base) > inv.company_id.currency_id.rounding:
                        raise osv.except_osv(_('Warning !'), _('Tax base different !\nClick on compute to update tax base'))
                for key in compute_taxes:
                    if not key in tax_key:
                        raise osv.except_osv(_('Warning !'), _('Taxes missing !'))

            if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding/2.0):
                raise osv.except_osv(_('Bad total !'), _('Please verify the price of the invoice !\nThe real total does not match the computed total.'))

            # one move line per tax line
            iml += ait_obj.move_line_get(cr, uid, inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = self._convert_ref(cr, uid, inv.number)

            diff_currency_p = inv.currency_id.id <> company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
            for i in iml:
                if inv.currency_id.id != company_currency:
                    i['currency_id'] = inv.currency_id.id
                    i['amount_currency'] = i['price']
                    i['price'] = cur_obj.compute(cr, uid, inv.currency_id.id,
                            company_currency, i['price'],
                            context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')})
                else:
                    i['amount_currency'] = False
                    i['currency_id'] = False
                i['ref'] = ref
                if inv.type in ('out_invoice','in_refund'):
                    total += i['price']
                    total_currency += i['amount_currency'] or i['price']
                    i['price'] = - i['price']
                else:
                    total -= i['price']
                    total_currency -= i['amount_currency'] or i['price']
            acc_id = inv.account_id.id

            name = inv['name'] or '/'
            totlines = False
            if inv.payment_term:
                totlines = self.pool.get('account.payment.term').compute(cr,
                        uid, inv.payment_term.id, total, inv.date_invoice or False)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid,
                                company_currency, inv.currency_id.id, t[1])
                    else:
                        amount_currency = False

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': acc_id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency_p \
                                and  amount_currency or False,
                        'currency_id': diff_currency_p \
                                and inv.currency_id.id or False,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': acc_id,
                    'date_maturity' : inv.date_due or False,
                    'amount_currency': diff_currency_p \
                            and total_currency or False,
                    'currency_id': diff_currency_p \
                            and inv.currency_id.id or False,
                    'ref': ref
            })

            date = inv.date_invoice or time.strftime('%Y-%m-%d')
            part = inv.partner_id.id

            line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part, date, context={})) ,iml)

            if inv.journal_id.group_invoice_lines:
                line2 = {}
                for x, y, l in line:
                    tmp = str(l['account_id'])
                    tmp += '-'+str(l.get('tax_code_id',"False"))
                    tmp += '-'+str(l.get('product_id',"False"))
                    tmp += '-'+str(l.get('analytic_account_id',"False"))
                    tmp += '-'+str(l.get('date_maturity',"False"))
                    
                    if tmp in line2:
                        am = line2[tmp]['debit'] - line2[tmp]['credit'] + (l['debit'] - l['credit'])
                        line2[tmp]['debit'] = (am > 0) and am or 0.0
                        line2[tmp]['credit'] = (am < 0) and -am or 0.0
                        line2[tmp]['tax_amount'] += l['tax_amount']
                        line2[tmp]['analytic_lines'] += l['analytic_lines']
                    else:
                        line2[tmp] = l
                line = []
                for key, val in line2.items():
                    line.append((0,0,val))

            journal_id = inv.journal_id.id #self._get_journal(cr, uid, {'type': inv['type']})
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
            if journal.centralisation:
                raise osv.except_osv(_('UserError'),
                        _('Cannot create invoice move on centralised journal'))

            line = self.finalize_invoice_move_lines(cr, uid, inv, line)

            move = {'ref': inv.number, 'line_id': line, 'journal_id': journal_id, 'date': date}
            period_id=inv.period_id and inv.period_id.id or False
            if not period_id:
                period_ids= self.pool.get('account.period').search(cr,uid,[('date_start','<=',inv.date_invoice or time.strftime('%Y-%m-%d')),('date_stop','>=',inv.date_invoice or time.strftime('%Y-%m-%d'))])
                if len(period_ids):
                    period_id=period_ids[0]
            if period_id:
                move['period_id'] = period_id
                for i in line:
                    i[2]['period_id'] = period_id

            move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
            new_move_name = self.pool.get('account.move').browse(cr, uid, move_id).name
            # make the invoice point to that move
            self.write(cr, uid, [inv.id], {'move_id': move_id,'period_id':period_id, 'move_name':new_move_name})
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            self.pool.get('account.move').post(cr, uid, [move_id], context={'invoice':inv})
        self._log_event(cr, uid, ids)
        return True

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        return {
            'date_maturity': x.get('date_maturity', False),
            'partner_id':part,
            'name':x['name'][:64],
            'date': date,
            'debit':x['price']>0 and x['price'],
            'credit':x['price']<0 and -x['price'],
            'account_id':x['account_id'],
            'analytic_lines':x.get('analytic_lines', []),
            'amount_currency':x['price']>0 and abs(x.get('amount_currency', False)) or -abs(x.get('amount_currency', False)),
            'currency_id':x.get('currency_id', False),
            'tax_code_id': x.get('tax_code_id', False),
            'tax_amount': x.get('tax_amount', False),
            'ref':x.get('ref',False),
            'quantity':x.get('quantity',1.00),
            'product_id':x.get('product_id', False),
            'product_uom_id':x.get('uos_id',False),
            'analytic_account_id':x.get('account_analytic_id',False),
        }

    def action_number(self, cr, uid, ids, *args):
        cr.execute('SELECT id, type, number, move_id, reference ' \
                   'FROM account_invoice ' \
                   'WHERE id IN %s',
                   (tuple(ids),))
        obj_inv = self.browse(cr, uid, ids)[0]
        for (id, invtype, number, move_id, reference) in cr.fetchall():
            if not number:
                tmp_context = {
                    'fiscalyear_id' : obj_inv.period_id.fiscalyear_id.id,
                }
                if obj_inv.journal_id.invoice_sequence_id:
                    sid = obj_inv.journal_id.invoice_sequence_id.id
                    number = self.pool.get('ir.sequence').get_id(cr, uid, sid, 'id=%s', context=tmp_context)
                else:
                    number = self.pool.get('ir.sequence').get_id(cr, uid,
                                                                 'account.invoice.' + invtype,
                                                                 'code=%s',
                                                                 context=tmp_context)
                if not number:
                    raise osv.except_osv(_('Warning !'), _('There is no active invoice sequence defined for the journal !'))

                if invtype in ('in_invoice', 'in_refund'):
                    ref = reference
                else:
                    ref = self._convert_ref(cr, uid, number)
                cr.execute('UPDATE account_invoice SET number=%s ' \
                        'WHERE id=%s', (number, id))
                cr.execute('UPDATE account_move SET ref=%s ' \
                        'WHERE id=%s AND (ref is null OR ref = \'\')',
                        (ref, move_id))
                cr.execute('UPDATE account_move_line SET ref=%s ' \
                        'WHERE move_id=%s AND (ref is null OR ref = \'\')',
                        (ref, move_id))
                cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                        'FROM account_move_line ' \
                        'WHERE account_move_line.move_id = %s ' \
                            'AND account_analytic_line.move_id = account_move_line.id',
                            (ref, move_id))
        return True

    def action_cancel(self, cr, uid, ids, *args):
        account_move_obj = self.pool.get('account.move')
        invoices = self.read(cr, uid, ids, ['move_id', 'payment_ids'])
        for i in invoices:
            if i['move_id']:
                account_move_obj.button_cancel(cr, uid, [i['move_id'][0]])
                # delete the move this invoice was pointing to
                # Note that the corresponding move_lines and move_reconciles
                # will be automatically deleted too
                account_move_obj.unlink(cr, uid, [i['move_id'][0]])
            if i['payment_ids']:
                account_move_line_obj = self.pool.get('account.move.line')
                pay_ids = account_move_line_obj.browse(cr, uid , i['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        raise osv.except_osv(_('Error !'), _('You cannot cancel the Invoice which is Partially Paid! You need to unreconcile concerned payment entries!'))

        self.write(cr, uid, ids, {'state':'cancel', 'move_id':False})
        self._log_event(cr, uid, ids,-1.0, 'Cancel Invoice')
        return True

    ###################

    def list_distinct_taxes(self, cr, uid, ids):
        invoices = self.browse(cr, uid, ids)
        taxes = {}
        for inv in invoices:
            for tax in inv.tax_line:
                if not tax['name'] in taxes:
                    taxes[tax['name']] = {'name': tax['name']}
        return taxes.values()

    def _log_event(self, cr, uid, ids, factor=1.0, name='Open Invoice'):
        invs = self.read(cr, uid, ids, ['type','partner_id','amount_untaxed'])
        for inv in invs:
            part=inv['partner_id'] and inv['partner_id'][0]
            pc = pr = 0.0
            cr.execute('select sum(quantity*price_unit) from account_invoice_line where invoice_id=%s', (inv['id'],))
            total = inv['amount_untaxed']
            if inv['type'] in ('in_invoice','in_refund'):
                partnertype='supplier'
                eventtype = 'purchase'
                pc = total*factor
            else:
                partnertype = 'customer'
                eventtype = 'sale'
                pr = total*factor
            if self.pool.get('res.partner.event.type').check(cr, uid, 'invoice_open'):
                self.pool.get('res.partner.event').create(cr, uid, {'name':'Invoice: '+name, 'som':False, 'description':name+' '+str(inv['id']), 'document':name, 'partner_id':part, 'date':time.strftime('%Y-%m-%d %H:%M:%S'), 'canal_id':False, 'user_id':uid, 'partner_type':partnertype, 'probability':1.0, 'planned_revenue':pr, 'planned_cost':pc, 'type':eventtype})
        return len(invs)

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        types = {
                'out_invoice': 'CI: ',
                'in_invoice': 'SI: ',
                'out_refund': 'OR: ',
                'in_refund': 'SR: ',
                }
        return [(r['id'], types[r['type']]+(r['number'] or '')+' '+(r['name'] or '')) for r in self.read(cr, uid, ids, ['type', 'number', 'name'], context, load='_classic_write')]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args=[]
        if context is None:
            context={}
        ids = []
        if name:
            ids = self.search(cr, user, [('number','=',name)]+ args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def _refund_cleanup_lines(self, cr, uid, lines):
        for line in lines:
            del line['id']
            del line['invoice_id']
            if 'account_id' in line:
                line['account_id'] = line.get('account_id', False) and line['account_id'][0]
            if 'product_id' in line:
                line['product_id'] = line.get('product_id', False) and line['product_id'][0]
            if 'uos_id' in line:
                line['uos_id'] = line.get('uos_id', False) and line['uos_id'][0]
            if 'invoice_line_tax_id' in line:
                line['invoice_line_tax_id'] = [(6,0, line.get('invoice_line_tax_id', [])) ]
            if 'account_analytic_id' in line:
                line['account_analytic_id'] = line.get('account_analytic_id', False) and line['account_analytic_id'][0]
            if 'tax_code_id' in line :
                if isinstance(line['tax_code_id'],tuple)  and len(line['tax_code_id']) >0 :
                    line['tax_code_id'] = line['tax_code_id'][0]
            if 'base_code_id' in line :
                if isinstance(line['base_code_id'],tuple)  and len(line['base_code_id']) >0 :
                    line['base_code_id'] = line['base_code_id'][0]
        return map(lambda x: (0,0,x), lines)

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None):
        invoices = self.read(cr, uid, ids, ['name', 'type', 'number', 'reference', 'comment', 'date_due', 'partner_id', 'address_contact_id', 'address_invoice_id', 'partner_contact', 'partner_insite', 'partner_ref', 'payment_term', 'account_id', 'currency_id', 'invoice_line', 'tax_line', 'journal_id'])

        new_ids = []
        for invoice in invoices:
            del invoice['id']

            type_dict = {
                'out_invoice': 'out_refund', # Customer Invoice
                'in_invoice': 'in_refund',   # Supplier Invoice
                'out_refund': 'out_invoice', # Customer Refund
                'in_refund': 'in_invoice',   # Supplier Refund
            }


            invoice_lines = self.pool.get('account.invoice.line').read(cr, uid, invoice['invoice_line'])
            invoice_lines = self._refund_cleanup_lines(cr, uid, invoice_lines)

            tax_lines = self.pool.get('account.invoice.tax').read(cr, uid, invoice['tax_line'])
            tax_lines = filter(lambda l: l['manual'], tax_lines)
            tax_lines = self._refund_cleanup_lines(cr, uid, tax_lines)
            if not date :
                date = time.strftime('%Y-%m-%d')
            invoice.update({
                'type': type_dict[invoice['type']],
                'date_invoice': date,
                'state': 'draft',
                'number': False,
                'invoice_line': invoice_lines,
                'tax_line': tax_lines
            })
            if period_id :
                invoice.update({
                    'period_id': period_id,
                })
            if description :
                invoice.update({
                    'name': description,
                })
            # take the id part of the tuple returned for many2one fields
            for field in ('address_contact_id', 'address_invoice_id', 'partner_id',
                    'account_id', 'currency_id', 'payment_term', 'journal_id'):
                invoice[field] = invoice[field] and invoice[field][0]
            # create the new invoice
            new_ids.append(self.create(cr, uid, invoice))
        return new_ids

    def pay_and_reconcile(self, cr, uid, ids, pay_amount, pay_account_id, period_id, pay_journal_id, writeoff_acc_id, writeoff_period_id, writeoff_journal_id, context=None, name=''):
        if context is None:
            context = {}
        #TODO check if we can use different period for payment and the writeoff line
        assert len(ids)==1, "Can only pay one invoice at a time"
        invoice = self.browse(cr, uid, ids[0])
        src_account_id = invoice.account_id.id
        # Take the seq as name for move
        types = {'out_invoice': -1, 'in_invoice': 1, 'out_refund': 1, 'in_refund': -1}
        direction = types[invoice.type]
        #take the choosen date
        if 'date_p' in context and context['date_p']:
            date=context['date_p']
        else:
            date=time.strftime('%Y-%m-%d')
            
        # Take the amount in currency and the currency of the payment
        if 'amount_currency' in context and context['amount_currency'] and 'currency_id' in context and context['currency_id']:
            amount_currency = context['amount_currency']
            currency_id = context['currency_id']
        else:
            amount_currency = False
            currency_id = False
        
        if invoice.type in ('in_invoice', 'in_refund'):
            ref = invoice.reference
        else:
            ref = self._convert_ref(cr, uid, invoice.number)        
        # Pay attention to the sign for both debit/credit AND amount_currency
        l1 = {
            'debit': direction * pay_amount>0 and direction * pay_amount,
            'credit': direction * pay_amount<0 and - direction * pay_amount,
            'account_id': src_account_id,
            'partner_id': invoice.partner_id.id,
            'ref':ref,
            'date': date,
            'currency_id':currency_id,
            'amount_currency':amount_currency and direction * amount_currency or 0.0,
        }
        l2 = {
            'debit': direction * pay_amount<0 and - direction * pay_amount,
            'credit': direction * pay_amount>0 and direction * pay_amount,
            'account_id': pay_account_id,
            'partner_id': invoice.partner_id.id,
            'ref':ref,
            'date': date,
            'currency_id':currency_id,
            'amount_currency':amount_currency and - direction * amount_currency or 0.0,
        }

        if not name:
            name = invoice.invoice_line and invoice.invoice_line[0].name or invoice.number
        l1['name'] = name
        l2['name'] = name

        lines = [(0, 0, l1), (0, 0, l2)]
        move = {'ref': ref, 'line_id': lines, 'journal_id': pay_journal_id, 'period_id': period_id, 'date': date}
        move_id = self.pool.get('account.move').create(cr, uid, move, context=context)

        line_ids = []
        total = 0.0
        line = self.pool.get('account.move.line')
        cr.execute('SELECT id FROM account_move_line '\
                   'WHERE move_id in %s',
                   ((move_id, invoice.move_id.id),))
        lines = line.browse(cr, uid, map(lambda x: x[0], cr.fetchall()) )

        for l in lines+invoice.payment_ids:
            if l.account_id.id==src_account_id:
                line_ids.append(l.id)
                total += (l.debit or 0.0) - (l.credit or 0.0)

        if (not round(total,int(config['price_accuracy']))) or writeoff_acc_id:
            self.pool.get('account.move.line').reconcile(cr, uid, line_ids, 'manual', writeoff_acc_id, writeoff_period_id, writeoff_journal_id, context)
        else:
            self.pool.get('account.move.line').reconcile_partial(cr, uid, line_ids, 'manual', context)

        # Update the stored value (fields.function), so we write to trigger recompute
        self.pool.get('account.invoice').write(cr, uid, ids, {}, context=context)
        return True
account_invoice()

class account_invoice_line(osv.osv):
    def _amount_line(self, cr, uid, ids, prop, unknow_none,unknow_dict):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            if line.invoice_id:
                res[line.id] = line.price_unit * line.quantity * (1-(line.discount or 0.0)/100.0)
                cur = line.invoice_id.currency_id
                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
            else:
                res[line.id] = round(line.price_unit * line.quantity * (1-(line.discount or 0.0)/100.0),int(config['price_accuracy']))
        return res


    def _price_unit_default(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'check_total' in context:
            t = context['check_total']
            for l in context.get('invoice_line', {}):
                if isinstance(l, (list, tuple)) and len(l) >= 3 and l[2]:
                    tax_obj = self.pool.get('account.tax')
                    p = l[2].get('price_unit', 0) * (1-l[2].get('discount', 0)/100.0)
                    t = t - (p * l[2].get('quantity'))
                    taxes = l[2].get('invoice_line_tax_id')
                    if len(taxes[0]) >= 3 and taxes[0][2]:
                        taxes=tax_obj.browse(cr, uid, taxes[0][2])
                        for tax in tax_obj.compute(cr, uid, taxes, p,l[2].get('quantity'), context.get('address_invoice_id', False), l[2].get('product_id', False), context.get('partner_id', False)):
                            t = t - tax['amount']
            return t
        return 0

    _name = "account.invoice.line"
    _description = "Invoice line"
    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'origin': fields.char('Origin', size=256, help="Reference of the document that produced this invoice."),
        'invoice_id': fields.many2one('account.invoice', 'Invoice Ref', ondelete='cascade', select=True),
        'uos_id': fields.many2one('product.uom', 'Unit of Measure', ondelete='set null'),
        'product_id': fields.many2one('product.product', 'Product', ondelete='set null'),
        'account_id': fields.many2one('account.account', 'Account', required=True, domain=[('type','<>','view'), ('type', '<>', 'closed')], help="The income or expense account related to the selected product."),
        'price_unit': fields.float('Unit Price', required=True, digits=(16, int(config['price_accuracy']))),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal',store=True, type="float", digits=(16, int(config['price_accuracy']))),
        'quantity': fields.float('Quantity', required=True),
        'discount': fields.float('Discount (%)', digits=(16, int(config['price_accuracy']))),
        'invoice_line_tax_id': fields.many2many('account.tax', 'account_invoice_line_tax', 'invoice_line_id', 'tax_id', 'Taxes', domain=[('parent_id','=',False)]),
        'note': fields.text('Notes'),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account'),
    }
    _defaults = {
        'quantity': lambda *a: 1,
        'discount': lambda *a: 0.0,
        'price_unit': _price_unit_default,
    }

    def product_id_change_unit_price_inv(self, cr, uid, tax_id, price_unit, qty, address_invoice_id, product, partner_id, context=None):
        tax_obj = self.pool.get('account.tax')
        if price_unit:
            taxes = tax_obj.browse(cr, uid, tax_id)
            for tax in tax_obj.compute_inv(cr, uid, taxes, price_unit, qty, address_invoice_id, product, partner_id):
                price_unit = price_unit - tax['amount']
        return {'price_unit': price_unit,'invoice_line_tax_id': tax_id}

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, context=None):
        if context is None:
            context = {}
        if not partner_id:
            raise osv.except_osv(_('No Partner Defined !'),_("You must first select a partner !") )
        if not product:
            if type in ('in_invoice', 'in_refund'):
                return {'value':{}, 'domain':{'product_uom':[]}}
            else:
                return {'value': {'price_unit': 0.0}, 'domain':{'product_uom':[]}}
        part = self.pool.get('res.partner').browse(cr, uid, partner_id)
        fpos = fposition_id and self.pool.get('account.fiscal.position').browse(cr, uid, fposition_id) or False

        if part.lang:
            context.update({'lang': part.lang})
        result = {}
        res = self.pool.get('product.product').browse(cr, uid, product, context=context)

        if type in ('out_invoice','out_refund'):
            a =  res.product_tmpl_id.property_account_income.id
            if not a:
                a = res.categ_id.property_account_income_categ.id
        else:
            a =  res.product_tmpl_id.property_account_expense.id
            if not a:
                a = res.categ_id.property_account_expense_categ.id

        a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, a)
        if a:
            result['account_id'] = a

        taxep=None
        tax_obj = self.pool.get('account.tax')
        if type in ('out_invoice', 'out_refund'):
            taxes = res.taxes_id and res.taxes_id or (a and self.pool.get('account.account').browse(cr, uid,a).tax_ids or False)
            tax_id = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)
        else:
            taxes = res.supplier_taxes_id and res.supplier_taxes_id or (a and self.pool.get('account.account').browse(cr, uid,a).tax_ids or False)
            tax_id = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)
        if type in ('in_invoice', 'in_refund'):
            to_update = self.product_id_change_unit_price_inv(cr, uid, tax_id, price_unit or res.standard_price, qty, address_invoice_id, product, partner_id, context=context)
            result.update(to_update)
        else:
            result.update({'price_unit': res.list_price, 'invoice_line_tax_id': tax_id})

        if not name:
            result['name'] = res.partner_ref

        domain = {}
        result['uos_id'] = uom or res.uom_id.id or False
        result['note'] = res.description
        if result['uos_id']:
            res2 = res.uom_id.category_id.id
            if res2 :
                domain = {'uos_id':[('category_id','=',res2 )]}
        return {'value':result, 'domain':domain}

    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = []
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        ait_obj = self.pool.get('account.invoice.tax')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id)
        company_currency = inv.company_id.currency_id.id
        cur = inv.currency_id

        for line in inv.invoice_line:
            mres = self.move_line_get_item(cr, uid, line, context)
            if not mres:
                continue
            res.append(mres)
            tax_code_found= False
            for tax in tax_obj.compute(cr, uid, line.invoice_line_tax_id,
                    (line.price_unit * (1.0 - (line['discount'] or 0.0) / 100.0)),
                    line.quantity, inv.address_invoice_id.id, line.product_id,
                    inv.partner_id):

                if inv.type in ('out_invoice', 'in_invoice'):
                    tax_code_id = tax['base_code_id']
                    tax_amount = line.price_subtotal * tax['base_sign']
                else:
                    tax_code_id = tax['ref_base_code_id']
                    tax_amount = line.price_subtotal * tax['ref_base_sign']

                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(self.move_line_get_item(cr, uid, line, context))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True

                res[-1]['tax_code_id'] = tax_code_id
                res[-1]['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, tax_amount, context={'date': inv.date_invoice})
        return res

    def move_line_get_item(self, cr, uid, line, context=None):
        return {
            'type':'src',
            'name': line.name[:64],
            'price_unit':line.price_unit,
            'quantity':line.quantity,
            'price':line.price_subtotal,
            'account_id':line.account_id.id,
            'product_id':line.product_id.id,
            'uos_id':line.uos_id.id,
            'account_analytic_id':line.account_analytic_id.id,
            'taxes':line.invoice_line_tax_id,
        }
    #
    # Set the tax field according to the account and the fiscal position
    #
    def onchange_account_id(self, cr, uid, ids, fposition_id, account_id):
        if not account_id:
            return {}
        taxes = self.pool.get('account.account').browse(cr, uid, account_id).tax_ids
        fpos = fposition_id and self.pool.get('account.fiscal.position').browse(cr, uid, fposition_id) or False
        res = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)
        r = {'value':{'invoice_line_tax_id': res}}
        return r
account_invoice_line()

class account_invoice_tax(osv.osv):
    _name = "account.invoice.tax"
    _description = "Invoice Tax"
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice Line', ondelete='cascade', select=True),
        'name': fields.char('Tax Description', size=64, required=True),
        'account_id': fields.many2one('account.account', 'Tax Account', required=True, domain=[('type','<>','view'),('type','<>','income'), ('type', '<>', 'closed')]),
        'base': fields.float('Base', digits=(16,int(config['price_accuracy']))),
        'amount': fields.float('Amount', digits=(16,int(config['price_accuracy']))),
        'manual': fields.boolean('Manual'),
        'sequence': fields.integer('Sequence'),

        'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration."),
        'base_amount': fields.float('Base Code Amount', digits=(16,int(config['price_accuracy']))),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration."),
        'tax_amount': fields.float('Tax Code Amount', digits=(16,int(config['price_accuracy']))),
    }
    
    def base_change(self, cr, uid, ids, base,currency_id=False,company_id=False,date_invoice=False):
        cur_obj = self.pool.get('res.currency')
        company_obj = self.pool.get('res.company')
        company_currency=False
        if company_id:            
            company_currency = company_obj.read(cr,uid,[company_id],['currency_id'])[0]['currency_id'][0]
        if currency_id and company_currency:
            base = cur_obj.compute(cr, uid, currency_id, company_currency, base, context={'date': date_invoice or time.strftime('%Y-%m-%d')}, round=False)
        return {'value': {'base_amount':base}}

    def amount_change(self, cr, uid, ids, amount,currency_id=False,company_id=False,date_invoice=False):
        cur_obj = self.pool.get('res.currency')
        company_obj = self.pool.get('res.company')
        company_currency=False
        if company_id:
            company_currency = company_obj.read(cr,uid,[company_id],['currency_id'])[0]['currency_id'][0]
        if currency_id and company_currency:
            amount = cur_obj.compute(cr, uid, currency_id, company_currency, amount, context={'date': date_invoice or time.strftime('%Y-%m-%d')}, round=False)
        return {'value': {'tax_amount':amount}}
    
    _order = 'sequence'
    _defaults = {
        'manual': lambda *a: 1,
        'base_amount': lambda *a: 0.0,
        'tax_amount': lambda *a: 0.0,
    }
    def compute(self, cr, uid, invoice_id, context={}):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context)
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id.id

        for line in inv.invoice_line:
            for tax in tax_obj.compute(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id):
                val={}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = tax['price_unit'] * line['quantity']

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped

    def move_line_get(self, cr, uid, invoice_id):
        res = []
        cr.execute('SELECT * FROM account_invoice_tax WHERE invoice_id=%s', (invoice_id,))
        for t in cr.dictfetchall():
            if not t['amount'] \
                    and not t['tax_code_id'] \
                    and not t['tax_amount']:
                continue
            res.append({
                'type':'tax',
                'name':t['name'],
                'price_unit': t['amount'],
                'quantity': 1,
                'price': t['amount'] or 0.0,
                'account_id': t['account_id'],
                'tax_code_id': t['tax_code_id'],
                'tax_amount': t['tax_amount']
            })
        return res
account_invoice_tax()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

