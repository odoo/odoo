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
from openerp.tools import float_compare


class account_voucher(models.Model):

    @api.one
    @api.depends('move_id.line_id.reconciled', 'move_id.line_id.account_id.internal_type')
    def _check_paid(self):
        self.paid = any([((line.account_id.internal_type, 'in', ('receivable', 'payable')) and line.reconciled) for line in self.move_id.line_id])

    @api.model
    def _get_currency(self):
        journal = self.env['account.journal'].browse(self._context.get('journal_id', False))
        if journal.currency:
            return journal.currency.id
        return self.env.user.company_id.currency_id.id

    @api.multi
    @api.depends('name', 'number')
    def name_get(self):
        return [(r.id, (r.number or _('Voucher'))) for r in self]

    @api.one
    @api.depends('journal_id', 'company_id')
    def _get_journal_currency(self):
        self.currency_id = self.journal_id.currency and self.journal_id.currency.id or self.company_id.currency_id.id

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
    name = fields.Char('Memo', readonly=True, states={'draft': [('readonly', False)]}, default='')
    date = fields.Date('Date', readonly=True, select=True, states={'draft': [('readonly', False)]},
                           help="Effective date for accounting entries", copy=False, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft': [('readonly', False)]})
    account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain=[('deprecated', '=', False)])
    line_ids = fields.One2many('account.voucher.line', 'voucher_id', 'Voucher Lines',
                                   readonly=True, copy=True,
                                   states={'draft': [('readonly', False)]})
    narration = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', compute='_get_journal_currency', string='Currency', readonly=True, required=True, default=lambda self: self._get_currency())
    company_id = fields.Many2one('res.company', 'Company', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('account.voucher'))
    state = fields.Selection(
            [('draft', 'Draft'),
             ('cancel', 'Cancelled'),
             ('proforma', 'Pro-forma'),
             ('posted', 'Posted')
            ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Voucher. \
                        \n* The \'Pro-forma\' when voucher is in Pro-forma status,voucher does not have an voucher number. \
                        \n* The \'Posted\' status is used when user create voucher,a voucher number is generated and voucher entries are created in account \
                        \n* The \'Cancelled\' status is used when user cancel voucher.')
    reference = fields.Char('Ref #', readonly=True, states={'draft': [('readonly', False)]},
                                 help="Transaction reference number.", copy=False)
    amount = fields.Float(string='Total', digits=dp.get_precision('Account'), required=True, readonly=True, states={'draft': [('readonly', False)]})
    tax_amount = fields.Float(string='Tax Amount', digits=dp.get_precision('Account'), readonly=True)
    number = fields.Char('Number', readonly=True, copy=False)
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    partner_id = fields.Many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'draft': [('readonly', False)]})
    paid = fields.Boolean(compute='_check_paid', string='Paid', help="The Voucher has been totally paid.")
    pay_now = fields.Selection([
            ('pay_now', 'Pay Directly'),
            ('pay_later', 'Pay Later or Group Funds'),
        ], 'Payment', select=True, readonly=True, states={'draft': [('readonly', False)]}, default='pay_now')
    date_due = fields.Date('Due Date', readonly=True, select=True, states={'draft': [('readonly', False)]})

    @api.multi
    def compute_tax(self):
        Tax_Obj = self.env['account.tax']
        for voucher in self:
            voucher_amount = 0.0
            total = 0.0
            total_tax = 0.0
            for line in voucher.line_ids:
                voucher_amount += line.price_subtotal
                if not line.tax_ids:
                    voucher.write({'amount': voucher_amount, 'tax_amount': 0.0})
                    continue

                tax = line.tax_ids
                partner = voucher.partner_id or False
                taxes = self.env['account.fiscal.position'].map_tax(tax)
                tax = Tax_Obj.browse(taxes.ids)

                total = voucher_amount
                if not tax[0].price_include:
                    for tax_line in tax.compute_all((line.price_unit * line.quantity), self.currency_id).get('taxes', []):
                        total_tax += tax_line.get('amount', 0.0)
                    total += total_tax
                else:
                    line_total = 0.0
                    line_tax = 0.0

                    for tax_line in tax.compute_all((line.price_unit * line.quantity), self.currency_id).get('taxes', []):
                        line_tax += tax_line.get('amount', 0.0)
                        line_total += tax_line.get('price_unit')
                    total_tax += line_tax

            voucher.write({'amount': total, 'tax_amount': total_tax})
        return True

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.journal_id.type == 'sale':
            account_id = self.partner_id.property_account_receivable.id
        elif self.journal_id.type == 'purchase':
            account_id = self.partner_id.property_account_payable.id
        else:
            account_id = self.journal_id.default_credit_account_id.id or self.journal_id.default_debit_account_id.id
        self.account_id = account_id

    @api.multi
    def button_proforma_voucher(self):
        self.signal_workflow('proforma_voucher')
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def proforma_voucher(self):
        self.action_move_line_create()

    @api.multi
    def action_cancel_draft(self):
        self.create_workflow()
        self.write({'state':'draft'})

    @api.multi
    def cancel_voucher(self):
        for voucher in self:
            voucher.move_id.button_cancel()
            voucher.move_id.unlink()
        self.write({'state': 'cancel', 'move_id': False})

    @api.multi
    def unlink(self):
        for voucher in self:
            if voucher.state not in ('draft', 'cancel'):
                raise Warning(_('Cannot delete voucher(s) which are already opened or paid.'))
        return super(account_voucher, self).unlink()

    @api.onchange('pay_now')
    def onchange_payment(self):
        account_id = False
        if self.pay_now == 'pay_later':
            partner = self.partner_id
            journal = self.journal_id
            if journal.type == 'sale':
                account_id = partner.property_account_receivable.id
            elif journal.type == 'purchase':
                account_id = partner.property_account_payable.id
            else:
                account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
        self.account_id = account_id

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        for voucher in self:
            debit = credit = 0.0
            if voucher.voucher_type == 'purchase':
                credit = voucher._convert_amount(amount)
            elif voucher.voucher_type == 'sale':
                debit = voucher._convert_amount(amount)
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
                    'currency_id': company_currency <> current_currency and current_currency or False,
                    'amount_currency': (sign * abs(voucher.amount)  # amount < 0 for refunds
                        if company_currency != current_currency else 0.0),
                    'date': voucher.date,
                    'date_maturity': voucher.date_due
                }
            return move_line

    @api.multi
    def account_move_get(self):
        for voucher in self:
            if voucher.number:
                name = voucher.number
            elif voucher.journal_id.sequence_id:
                if not voucher.journal_id.sequence_id.active:
                    raise Warning(_('Please activate the sequence of selected journal !'))
                name = voucher.journal_id.sequence_id.next_by_id()
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

    @api.multi
    def _convert_amount(self, amount):
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
        for voucher in self:
            return voucher.currency_id.compute(amount, voucher.company_id.currency_id)

    @api.multi
    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
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
        for voucher in self:
            tot_line = line_total
            date = voucher.date
            ctx = self._context.copy()
            ctx['date'] = date
            self.with_context(ctx)
            prec = self.env['decimal.precision'].precision_get('Account')
            for line in voucher.line_ids:
                #create one move line per voucher line where amount is not 0.0
                # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
                if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                    continue
                # convert the amount set on the voucher line into the currency of the voucher's company
                # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
                amount = voucher._convert_amount(line.untax_amount or line.amount)
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
                self.env['account.move.line'].create(move_line)
        return tot_line


    @api.multi
    def _get_company_currency(self):
        '''
        Get the currency of the actual company.
        :param voucher_id: Id of the voucher what i want to obtain company currency.
        :return: currency id of the company of the voucher
        :rtype: int
        '''
        for voucher in self:
            return voucher.journal_id.company_id.currency_id.id

    @api.multi
    def _get_current_currency(self):
        '''
        Get the currency of the voucher.
        :param voucher_id: Id of the voucher what i want to obtain current currency.
        :return: currency id of the voucher
        :rtype: int
        '''
        for voucher in self:
            return voucher.currency_id.id or voucher._get_company_currency()

    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        for voucher in self:
            local_context = dict(self._context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = voucher._get_company_currency()
            current_currency = voucher._get_current_currency()
            # we select the context to use accordingly if it's a multicurrency case or not
            context = voucher._sel_context()
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx['date'] = voucher.date
            # Create the account move record.
            move = self.env['account.move'].create(voucher.account_move_get())
            # Get the name of the account_move just created
            # Create the first line of the voucher
            move_line = self.env['account.move.line'].with_context(local_context).create(voucher.first_move_line_get(move.id, company_currency, current_currency))
            line_total = move_line.debit - move_line.credit
            if voucher.type == 'sale':
                line_total = line_total - voucher._convert_amount(voucher.tax_amount)
            elif voucher.type == 'purchase':
                line_total = line_total + voucher._convert_amount(voucher.tax_amount)
            # Create one move line per voucher line where amount is not 0.0
            line_total = voucher.voucher_move_line_create(line_total, move_id, company_currency, current_currency)

            # We post the voucher.
            voucher.write({
                'move_id': move.id,
                'state': 'posted',
                'number': move.name
            })
            if voucher.journal_id.entry_posted:
                move.post()
        return True


class account_voucher_line(models.Model):
    _name = 'account.voucher.line'
    _description = 'Voucher Lines'

    @api.one
    @api.depends('price_unit', 'tax_ids', 'quantity', 'product_id', 'voucher_id.currency_id')
    def _compute_subtotal(self):
        taxes = self.tax_ids.compute_all(self.price_unit, self.voucher_id.currency_id, self.quantity, product=self.product_id, partner=self.voucher_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

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
    tax_ids = fields.Many2many('account.tax', string='Tax', domain=[('price_include','=', False)], help="Only for tax excluded from price")
