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


from openerp import fields, models, api, _
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import float_compare
import openerp

class account_voucher(models.Model):
    def _check_paid(self, cr, uid, ids, name, args, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = any([((line.account_id.user_type.type, 'in', ('receivable', 'payable')) and line.reconcile_id) for line in voucher.move_id])
        return res

    def _get_currency(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_pool = self.pool.get('account.journal')
        journal_id = context.get('journal_id', False)
        if journal_id:
            journal = journal_pool.browse(cr, uid, journal_id, context=context)
            if journal.currency:
                return journal.currency.id
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None:
            context = {}
        return [(r['id'], (r['number'] or _('Voucher'))) for r in self.read(cr, uid, ids, ['number'], context, load='_classic_write')]

    def _get_journal_currency(self, cr, uid, ids, name, args, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] = voucher.journal_id.currency and voucher.journal_id.currency.id or voucher.company_id.currency_id.id
        return res

    _name = 'account.voucher'
    _description = 'Accounting Voucher'
    _inherit = ['mail.thread']
    _order = "date desc, id desc"
    _track = {
        'state': {
            'account_voucher.mt_voucher_state_change': lambda self, cr, uid, obj, ctx=None: True,
        },
    }

    voucher_type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')], string='Type', readonly=True, states={'draft': [('readonly', False)]})
    name = fields.Char('Memo', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Date', readonly=True, select=True, states={'draft': [('readonly', False)]},
                           help="Effective date for accounting entries", copy=False)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft': [('readonly', False)]})
    account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain=[('deprecated', '=', False)])
    line_ids = fields.One2many('account.voucher.line', 'voucher_id', 'Voucher Lines',
                                   readonly=True, copy=True,
                                   states={'draft': [('readonly', False)]})
    narration = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', compute='_get_journal_currency', string='Currency', readonly=True, required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(
            [('draft', 'Draft'),
             ('cancel', 'Cancelled'),
             ('proforma', 'Pro-forma'),
             ('posted', 'Posted')
            ], 'Status', readonly=True, track_visibility='onchange', copy=False,
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Voucher. \
                        \n* The \'Pro-forma\' when voucher is in Pro-forma status,voucher does not have an voucher number. \
                        \n* The \'Posted\' status is used when user create voucher,a voucher number is generated and voucher entries are created in account \
                        \n* The \'Cancelled\' status is used when user cancel voucher.')
    reference = fields.Char('Ref #', readonly=True, states={'draft': [('readonly', False)]},
                                 help="Transaction reference number.", copy=False)
    amount = fields.Float(string='Total', digits_compute=dp.get_precision('Account'), required=True, readonly=True, states={'draft':[('readonly',False)]})
    tax_amount = fields.Float(string='Tax Amount', digits_compute=dp.get_precision('Account'), readonly=True)
    number = fields.Char('Number', readonly=True, copy=False)
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    partner_id = fields.Many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'draft': [('readonly', False)]})
    paid = fields.Boolean(compute='_check_paid', string='Paid', help="The Voucher has been totally paid.")
    pay_now = fields.Selection([
            ('pay_now','Pay Directly'),
            ('pay_later','Pay Later or Group Funds'),
        ],'Payment', select=True, readonly=True, states={'draft':[('readonly',False)]})
    date_due = fields.Date('Due Date', readonly=True, select=True, states={'draft':[('readonly',False)]})

    _defaults = {
        'date': fields.Date.context_today,
        'currency_id': _get_currency,
        'state': 'draft',
        'pay_now': 'pay_now',
        'name': '',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
    }

    def compute_tax(self, cr, uid, ids, context=None):
        tax_pool = self.pool.get('account.tax')
        partner_pool = self.pool.get('res.partner')
        position_pool = self.pool.get('account.fiscal.position')
        voucher_line_pool = self.pool.get('account.voucher.line')
        voucher_pool = self.pool.get('account.voucher')
        if context is None: context = {}

        for voucher in voucher_pool.browse(cr, uid, ids, context=context):
            voucher_amount = 0.0
            for line in voucher.line_ids:
                voucher_amount += line.untax_amount or line.amount
                line.amount = line.untax_amount or line.amount
                voucher_line_pool.write(cr, uid, [line.id], {'amount':line.amount, 'untax_amount':line.untax_amount})

            if not voucher.tax_id:
                self.write(cr, uid, [voucher.id], {'amount': voucher_amount, 'tax_amount': 0.0})
                continue

            tax = [tax_pool.browse(cr, uid, voucher.tax_id.id, context=context)]
            partner = partner_pool.browse(cr, uid, voucher.partner_id.id, context=context) or False
            taxes = position_pool.map_tax(cr, uid, partner and partner.property_account_position or False, tax)
            tax = tax_pool.browse(cr, uid, taxes, context=context)

            total = voucher_amount
            total_tax = 0.0

            if not tax[0].price_include:
                for line in voucher.line_ids:
                    for tax_line in tax_pool.compute_all(cr, uid, tax, line.amount, 1).get('taxes', []):
                        total_tax += tax_line.get('amount', 0.0)
                total += total_tax
            else:
                for line in voucher.line_ids:
                    line_total = 0.0
                    line_tax = 0.0

                    for tax_line in tax_pool.compute_all(cr, uid, tax, line.untax_amount or line.amount, 1).get('taxes', []):
                        line_tax += tax_line.get('amount', 0.0)
                        line_total += tax_line.get('price_unit')
                    total_tax += line_tax
                    untax_amount = line.untax_amount or line.amount
                    voucher_line_pool.write(cr, uid, [line.id], {'amount':line_total, 'untax_amount':untax_amount})

            self.write(cr, uid, [voucher.id], {'amount':total, 'tax_amount':total_tax})
        return True

    def basic_onchange_partner(self, cr, uid, ids, partner_id, journal_id, ttype, context=None):
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        res = {'value': {'account_id': False}}
        if not partner_id or not journal_id:
            return res

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        res['value']['account_id'] = account_id
        return res

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        if not journal_id:
            return {}
        if context is None:
            context = {}
        #TODO: comment me and use me directly in the sales/purchases views
        res = self.basic_onchange_partner(cr, uid, ids, partner_id, journal_id, ttype, context=context)
        return res

    def button_proforma_voucher(self, cr, uid, ids, context=None):
        self.signal_workflow(cr, uid, ids, 'proforma_voucher')
        return {'type': 'ir.actions.act_window_close'}

    def proforma_voucher(self, cr, uid, ids, context=None):
        self.action_move_line_create(cr, uid, ids, context=context)
        return True

    def action_cancel_draft(self, cr, uid, ids, context=None):
        self.create_workflow(cr, uid, ids)
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def cancel_voucher(self, cr, uid, ids, context=None):
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            # refresh to make sure you don't unlink an already removed move
            voucher.refresh()
            if voucher.move_id:
                move_pool.button_cancel(cr, uid, [voucher.move_id.id])
                move_pool.unlink(cr, uid, [voucher.move_id.id])
        res = {
            'state':'cancel',
            'move_id':False,
        }
        self.write(cr, uid, ids, res)
        return True

    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] not in ('draft', 'cancel'):
                raise Warning(_('Cannot delete voucher(s) which are already opened or paid.'))
        return super(account_voucher, self).unlink(cr, uid, ids, context=context)

    def onchange_payment(self, cr, uid, ids, pay_now, journal_id, partner_id, ttype='sale'):
        res = {}
        if not partner_id:
            return res
        res = {}
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        if pay_now == 'pay_later':
            partner = partner_pool.browse(cr, uid, partner_id)
            journal = journal_pool.browse(cr, uid, journal_id)
            if journal.type in ('sale','sale_refund'):
                account_id = partner.property_account_receivable.id
            elif journal.type in ('purchase', 'purchase_refund','expense'):
                account_id = partner.property_account_payable.id
            else:
                account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
            if account_id:
                res['account_id'] = account_id
        return {'value':res}

    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        '''
        Return a dict to be use to create the first account move line of given voucher.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param move_id: Id of account move where this line will be added.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: mapping between fieldname and value of account move line to create
        :rtype: dict
        '''
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        debit = credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
        if voucher.type in ('purchase', 'payment'):
            credit = voucher.paid_amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = voucher.paid_amount_in_company_currency
        if debit < 0.0: debit = 0.0
        if credit < 0.0: credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        #set the first line of the voucher
        move_line = {
                'name': voucher.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': voucher.account_id.id,
                'move_id': move_id,
                'journal_id': voucher.journal_id.id,
                'partner_id': voucher.partner_id.id,
                'currency_id': company_currency <> current_currency and  current_currency or False,
                'amount_currency': (sign * abs(voucher.amount) # amount < 0 for refunds
                    if company_currency != current_currency else 0.0),
                'date': voucher.date,
                'date_maturity': voucher.date_due
            }
        return move_line

    def account_move_get(self, cr, uid, voucher_id, context=None):
        '''
        This method prepare the creation of the account move related to the given voucher.

        :param voucher_id: Id of voucher for which we are creating account_move.
        :return: mapping between fieldname and value of account move to create
        :rtype: dict
        '''
        seq_obj = self.pool.get('ir.sequence')
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        if voucher.number:
            name = voucher.number
        elif voucher.journal_id.sequence_id:
            if not voucher.journal_id.sequence_id.active:
                raise Warning(_('Please activate the sequence of selected journal !'))
            c = dict(context)
            name = seq_obj.next_by_id(cr, uid, voucher.journal_id.sequence_id.id, context=c)
        else:
            raise Warning(_('Please define a sequence on the journal.'))
        if not voucher.reference:
            ref = name.replace('/','')
        else:
            ref = voucher.reference

        move = {
            'name': name,
            'journal_id': voucher.journal_id.id,
            'narration': voucher.narration,
            'date': voucher.date,
            'ref': ref,
        }
        return move

    def _convert_amount(self, cr, uid, amount, voucher_id, context=None):
        '''
        This function convert the amount given in company currency. It takes either the rate in the voucher (if the
        payment_rate_currency_id is relevant) either the rate encoded in the system.

        :param amount: float. The amount to convert
        :param voucher: id of the voucher on which we want the conversion
        :param context: to context to use for the conversion. It may contain the key 'date' set to the voucher date
            field in order to select the good rate to use.
        :return: the amount in the currency of the voucher's company
        :rtype: float
        '''
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        voucher = self.browse(cr, uid, voucher_id, context=context)
        return currency_obj.compute(cr, uid, voucher.currency_id.id, voucher.company_id.currency_id.id, amount, context=context)

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        tot_line = line_total

        date = self.read(cr, uid, [voucher_id], ['date'], context=context)[0]['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        for line in voucher.line_ids:
            #create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            move_line = {
                'journal_id': voucher.journal_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            # compute the amount in foreign currency
            amount_currency = False

            move_line['amount_currency'] = amount_currency
            move_line_obj.create(cr, uid, move_line)

        return tot_line

    def _get_company_currency(self, cr, uid, voucher_id, context=None):
        '''
        Get the currency of the actual company.

        :param voucher_id: Id of the voucher what i want to obtain company currency.
        :return: currency id of the company of the voucher
        :rtype: int
        '''
        return self.pool.get('account.voucher').browse(cr,uid,voucher_id,context).journal_id.company_id.currency_id.id

    def _get_current_currency(self, cr, uid, voucher_id, context=None):
        '''
        Get the currency of the voucher.

        :param voucher_id: Id of the voucher what i want to obtain current currency.
        :return: currency id of the voucher
        :rtype: int
        '''
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        return voucher.currency_id.id or self._get_company_currency(cr,uid,voucher.id,context)

    def action_move_line_create(self, cr, uid, ids, context=None):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            local_context = dict(context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, voucher.id, context)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context), context=context)
            # Get the name of the account_move just created
            name = move_pool.browse(cr, uid, move_id, context=context).name
            # Create the first line of the voucher
            move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr,uid,voucher.id, move_id, company_currency, current_currency, local_context), local_context)
            move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
            line_total = move_line_brw.debit - move_line_brw.credit
            if voucher.type == 'sale':
                line_total = line_total - self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            elif voucher.type == 'purchase':
                line_total = line_total + self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            # Create one move line per voucher line where amount is not 0.0
            line_total = self.voucher_move_line_create(cr, uid, voucher.id, line_total, move_id, company_currency, current_currency, context)

            # We post the voucher.
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
        return True


class account_voucher_line(models.Model):
    _name = 'account.voucher.line'
    _description = 'Voucher Lines'

    @api.one
    @api.depends('price_unit', 'tax_ids', 'quantity', 'product_id', 'voucher_id.currency_id')
    def _compute_subtotal(self):
        #TODO deal with taxes
        #taxes = self.invoice_line_tax_id.compute_all(self.price_unit, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        #self.price_subtotal = taxes['total']
        self.price_subtotal = self.price_unit * self.quantity
        if self.voucher_id:
            self.price_subtotal = self.voucher_id.currency_id.round(self.price_subtotal)

    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10,
        help="Gives the sequence of this line when displaying the voucher.")
    voucher_id = fields.Many2one('account.voucher', 'Voucher', required=1, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
        ondelete='set null', index=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=True, domain=[('deprecated', '=', False)],
        help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True,
        digits=dp.get_precision('Product Price'))
    price_subtotal = fields.Float(string='Amount', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_subtotal')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    account_id = fields.Many2one('account.account','Account', required=True, domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    company_id = fields.Many2one('res.company', related='voucher_id.company_id', string='Company', store=True, readonly=True)
    tax_ids = fields.Many2many('account.tax', 'Tax', readonly=True, states={'draft':[('readonly',False)]}, domain=[('price_include','=', False)], help="Only for tax excluded from price")
