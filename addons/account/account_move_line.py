# -*- coding: utf-8 -*-

import time
from datetime import datetime

from openerp import workflow
from openerp import models, fields, api, _
from openerp.exceptions import Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp import tools
from openerp.report import report_sxw


class account_move_line(models.Model):
    _name = "account.move.line"
    _description = "Journal Items"
    _order = "date desc, id desc"

    @api.model
    def _query_get(self, obj='l'):
        fiscalyear_obj = self.env['account.fiscalyear']
        account_obj = self.env['account.account']
        fiscalyear_ids = []
        context = dict(self._context or {})
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        if context.get('company_id', False):
            company_clause = " AND " +obj+".company_id = %s" % context.get('company_id', False)
        if not context.get('fiscalyear', False):
            if context.get('all_fiscalyear', False):
                #this option is needed by the aged balance report because otherwise, if we search only the draft ones, an open invoice of a closed fiscalyear won't be displayed
                fiscalyear_ids = fiscalyear_obj.search([]).ids
            else:
                fiscalyear_ids = fiscalyear_obj.search([('state', '=', 'draft')]).ids
        else:
            #for initial balance as well as for normal query, we check only the selected FY because the best practice is to generate the FY opening entries
            fiscalyear_ids = [context['fiscalyear']]

        fiscalyear_clause = (','.join([str(x) for x in fiscalyear_ids])) or '0'
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        if context.get('date_from', False) and context.get('date_to', False):
            if initial_bal:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date < '" +context['date_from']+"')"
            else:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date >= '" +context['date_from']+"' AND date <= '"+context['date_to']+"')"

        if state:
            if state.lower() not in ['all']:
                where_move_state= " AND "+obj+".move_id IN (SELECT id FROM account_move WHERE account_move.state = '"+state+"')"
        if initial_bal and not context.get('periods', False) and not where_move_lines_by_date:
            #we didn't pass any filter in the context, and the initial balance can't be computed using only the fiscalyear otherwise entries will be summed twice
            #so we have to invalidate this query
            raise Warning(_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))


        if context.get('journal_ids', False):
            query += ' AND '+obj+'.journal_id IN (%s)' % ','.join(map(str, context['journal_ids']))

        if context.get('chart_account_id', False):
            child_ids = account_obj.browse(context['chart_account_id'])._get_children_and_consol()
            query += ' AND '+obj+'.account_id IN (%s)' % ','.join(map(str, child_ids))

        query += company_clause
        return query

    @api.model
    def _prepare_analytic_line(self, obj_line):
        """
        Prepare the values given at the create() of account.analytic.line upon the validation of a journal item having
        an analytic account. This method is intended to be extended in other modules.

        :param obj_line: browse record of the account.move.line that triggered the analytic line creation
        """
        return {'name': obj_line.name,
                'date': obj_line.date,
                'account_id': obj_line.analytic_account_id.id,
                'unit_amount': obj_line.quantity,
                'product_id': obj_line.product_id and obj_line.product_id.id or False,
                'product_uom_id': obj_line.product_uom_id and obj_line.product_uom_id.id or False,
                'amount': (obj_line.credit or  0.0) - (obj_line.debit or 0.0),
                'general_account_id': obj_line.account_id.id,
                'journal_id': obj_line.journal_id.analytic_journal_id.id,
                'ref': obj_line.ref,
                'move_id': obj_line.id,
                'user_id': self._uid,
               }

    @api.multi
    def create_analytic_lines(self):
        for obj_line in self:
            if obj_line.analytic_account_id:
                if not obj_line.journal_id.analytic_journal_id:
                    raise Warning(_("You have to define an analytic journal on the '%s' journal!") % (obj_line.journal_id.name, ))
                if obj_line.analytic_lines:
                    obj_line.analytic_lines.unlink()
                vals_line = obj_line._prepare_analytic_line()
                self.env['account.analytic.line'].create(vals_line)

    @api.multi
    @api.depends('ref', 'move_id')
    def name_get(self):
        result = []
        for line in self:
            if line.ref:
                result.append((line.id, (line.move_id.name or '') + '(' + line.ref + ')'))
            else:
                result.append((line.id, line.move_id.name))
        return result

    @api.multi
    @api.depends('reconcile_id','reconcile_partial_id')
    def _get_reconcile(self):
        for line in self:
            if line.reconcile_id:
                line.reconcile_ref = str(line.reconcile_id.name)
            elif line.reconcile_partial_id:
                line.reconcile_ref = str(line.reconcile_partial_id.name)
            # To get rid of Error: Field account.move.line.reconcile_ref is accessed before being computed.
            else:
                line.reconcile_ref = False

    name = fields.Char(string='Name', required=True)
    quantity = fields.Float(string='Quantity', digits=(16,2), 
        help="The optional quantity expressed by this line, eg: number of product sold. "\
        "The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    debit = fields.Float(string='Debit', digits=dp.get_precision('Account'), default=0.0)
    credit = fields.Float(string='Credit', digits=dp.get_precision('Account'), default=0.0)
    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
        ondelete="cascade", domain=[('deprecated', '=', False)],
        default=lambda self: self._context.get('account_id', False))
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade", 
        help="The move of this entry line.", index=True, required=True)
    narration = fields.Text(related='move_id.narration', string='Internal Note')
    ref = fields.Char(related='move_id.ref', string='Reference', store=True)
    statement_id = fields.Many2one('account.bank.statement', string='Statement', 
        help="The bank statement used for bank reconciliation", index=True, copy=False)
    reconcile_id = fields.Many2one('account.move.reconcile', string='Reconcile', 
        readonly=True, ondelete='set null', index=True, copy=False)
    reconcile_partial_id = fields.Many2one('account.move.reconcile', string='Partial Reconcile',
        readonly=True, ondelete='set null', index=True, copy=False)
    reconcile_ref = fields.Char(compute='_get_reconcile', string='Reconcile Ref', oldname='reconcile', store=True)
    amount_currency = fields.Float(string='Amount Currency', default=0.0,  digits=dp.get_precision('Account'),
        help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self._get_currency(), 
        help="The optional other currency if it is a multi-currency entry.")
    journal_id = fields.Many2one('account.journal', related='move_id.journal_id', string='Journal',
        default=lambda self: self._get_journal, required=True, index=True, store=True)
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")

    date_maturity = fields.Date(string='Due date', index=True ,
        help="This field is used for payable and receivable journal entries. "\
        "You can put the limit date for the payment of this line.")
    date = fields.Date(related='move_id.date', string='Effective date', required=True,
        index=True, default=fields.Date.context_today, store=True)
    analytic_lines = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines')

    # TODO: remove with the new tax engine
    tax_code_id = fields.Many2one('account.tax.code', string='Tax Account', 
        help="The Account can either be a base tax code or a tax code account.")
    tax_amount = fields.Float(string='Tax/Base Amount', digits=dp.get_precision('Account'), index=True, 
        help="If the Tax account is a tax code account, this field will contain the taxed amount."\
        "If the tax account is base tax code, this field will contain the basic amount(without tax).")

    account_tax_id = fields.Many2many('account.tax', string='Tax', copy=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    company_id = fields.Many2one('res.company', related='account_id.company_id',
        string='Company', store=True,
        default=lambda self: self.env['res.company']._company_default_get('account.move.line'))

    # TODO: put the invoice link and partner_id on the account_move
    invoice = fields.Many2one('account.invoice', string='Invoice')
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, ondelete='restrict')

    @api.model
    def _get_currency(self):
        currency = False
        context = dict(self._context or {})
        if context.get('default_journal_id', False):
            currency = self.env['account.journal'].browse(context['default_journal_id']).currency
        return currency

    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    @api.multi
    @api.constrains('account_id')
    def _check_account_type(self):
        for line in self:
            if line.account_id.type == 'consolidation':
                raise Warning(_('You cannot create journal items on an account of type view or consolidation.'))

    @api.multi
    @api.constrains('currency_id')
    def _check_currency(self):
        for line in self:
            if line.account_id.currency_id:
                if not line.currency_id or not line.currency_id.id == line.account_id.currency_id.id:
                    raise Warning(_('The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account or select a multi-currency view on the journal.'))

    @api.multi
    @api.constrains('currency_id','amount_currency')
    def _check_currency_and_amount(self):
        for line in self:
            if (line.amount_currency and not line.currency_id):
                raise Warning(_("You cannot create journal items with a secondary currency without recording both 'currency' and 'amount currency' field."))

    @api.multi
    @api.constrains('amount_currency')
    def _check_currency_amount(self):
        for line in self:
            if line.amount_currency:
                if (line.amount_currency > 0.0 and line.credit > 0.0) or (line.amount_currency < 0.0 and line.debit > 0.0):
                    raise Warning(_('The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.'))

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.date_maturity = False
        if self.partner_id:
            date = self.date or datetime.now().strftime('%Y-%m-%d')
            journal_type = self.journal_id.type
    
            payment_term_id = False
            if journal_type in ('purchase', 'purchase_refund') and self.partner_id.property_supplier_payment_term:
                payment_term_id = self.partner_id.property_supplier_payment_term.id
            elif self.partner_id.property_payment_term:
                payment_term_id = self.partner_id.property_payment_term.id
            if payment_term_id:
                res = self.env['account.payment.term'].compute(payment_term_id, 100, date)
                if res:
                    self.date_maturity = res[0][0]
            if not self.account_id:
                account_payable = self.partner_id.property_account_payable.id
                account_receivable =  self.partner_id.property_account_receivable.id
                if journal_type in ('sale', 'purchase_refund'):
                    self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_receivable)
                elif journal_type in ('purchase', 'sale_refund'):
                    self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_payable)
                elif journal_type in ('general', 'bank', 'cash'):
                    if self.partner_id.customer:
                        self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_receivable)
                    elif self.partner_id.supplier:
                        self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_payable)
                if self.account_id:
                    self.onchange_account_id()

    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.account_id:
            if self.account_id.tax_ids and self.partner_id:
                self.account_tax_id = self.env['account.fiscal.position'].map_tax(self.partner_id and self.partner_id.property_account_position or False, self.account_id.tax_ids)
            else:
                self.account_tax_id = self.account_id.tax_ids or False

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(self, target_currency=False, target_date=False):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param target_currency: curreny you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        if not self:
            return []
        company_currency = self.env.user.company_id.currency_id
        rml_parser = report_sxw.rml_parse(self._cr, self._uid, 'reconciliation_widget_aml', self._context)
        reconcile_partial_ids = []  # for a partial reconciliation, take only one line
        ret = []

        for line in self:
            if line.reconcile_partial_id and line.reconcile_partial_id.id in reconcile_partial_ids:
                continue
            if line.reconcile_partial_id:
                reconcile_partial_ids.append(line.reconcile_partial_id.id)

            ret_line = {
                'id': line.id,
                'name': line.move_id.name,
                'ref': line.move_id.ref,
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'journal_name': line.journal_id.name,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
            }

            # Get right debit / credit:
            line_currency = line.currency_id or company_currency
            amount_currency_str = ""
            if line.currency_id and line.amount_currency:
                amount_currency_str = rml_parser.formatLang(line.amount_currency, currency_obj=line.currency_id)
            if target_currency and line_currency == target_currency and target_currency != company_currency:
                debit = line.debit > 0 and line.amount_residual_currency or 0.0
                credit = line.credit > 0 and line.amount_residual_currency or 0.0
                amount_currency_str = rml_parser.formatLang(line.amount_residual, currency_obj=company_currency)
                amount_str = rml_parser.formatLang(debit or credit, currency_obj=target_currency)
            else:
                debit = line.debit > 0 and line.amount_residual or 0.0
                credit = line.credit > 0 and line.amount_residual or 0.0
                amount_str = rml_parser.formatLang(debit or credit, currency_obj=company_currency)
                if target_currency and target_currency != company_currency:
                    amount_currency_str = rml_parser.formatLang(debit or credit, currency_obj=line_currency)
                    ctx = context.copy()
                    if target_date:
                        ctx.update({'date': target_date})
                    debit = target_currency.with_context(ctx).compute(company_currency.id, debit)
                    credit = target_currency.with_context(ctx).compute(company_currency.id, credit)
                    amount_str = rml_parser.formatLang(debit or credit, currency_obj=target_currency)

            ret_line['credit'] = credit
            ret_line['debit'] = debit
            ret_line['amount_str'] = amount_str
            ret_line['amount_currency_str'] = amount_currency_str
            ret.append(ret_line)
        return ret

    @api.model
    def list_partners_to_reconcile(self):
        self._cr.execute(
             """SELECT partner_id FROM (
                SELECT l.partner_id, p.last_reconciliation_date, SUM(l.debit) AS debit, SUM(l.credit) AS credit, MAX(l.create_date) AS max_date
                FROM account_move_line l
                RIGHT JOIN account_account a ON (a.id = l.account_id)
                RIGHT JOIN res_partner p ON (l.partner_id = p.id)
                    WHERE a.reconcile IS TRUE
                    AND l.reconcile_id IS NULL
                    AND l.state != 'draft'
                    GROUP BY l.partner_id, p.last_reconciliation_date
                ) AS s
                WHERE debit > 0 AND credit > 0 AND (last_reconciliation_date IS NULL OR max_date > last_reconciliation_date)
                ORDER BY last_reconciliation_date""")
        ids = [x[0] for x in self._cr.fetchall()]
        if not ids:
            return []

        # To apply the ir_rules
        partners = self.env['res.partner'].search([('id', 'in', ids)])
        return partners.name_get()

    @api.multi
    def reconcile_partial(self, type='auto', writeoff_acc_id=False, writeoff_period_date=False, writeoff_journal_id=False):
        move_rec_obj = self.env['account.move.reconcile']
        merges = []
        unmerge = []
        total = 0.0
        merges_rec = []
        company_list = []
        for line in self:
            if company_list and not line.company_id.id in company_list:
                raise Warning(_('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)

        for line in self:
            if line.account_id.currency_id:
                currency_id = line.account_id.currency_id
            else:
                currency_id = line.company_id.currency_id
            if line.reconcile_id:
                raise Warning(_("Journal Item '%s' (id: %s), Move '%s' is already reconciled!") % (line.name, line.id, line.move_id.name))
            else:
                unmerge.append(line)
                if line.account_id.currency_id:
                    total += line.amount_currency
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0)
        if currency_id.is_zero(total):
            for line in merges+unmerge:
                res = line.reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_period_date=writeoff_period_date, writeoff_journal_id=writeoff_journal_id)
            return res
        # marking the lines as reconciled does not change their validity, so there is no need
        # to revalidate their moves completely.
        reconcile_context = dict(self._context, novalidate=True)
        r_id = move_rec_obj.with_context(reconcile_context).create({
            'type': type,
        })
        recs = [r_id] + merges_rec
        recs.with_context(reconcile_context).reconcile_partial_check()
        return r_id

    @api.multi
    def reconcile(self, type='auto', writeoff_acc_id=False, writeoff_period_date=False, writeoff_journal_id=False):
        unrec_lines = filter(lambda x: not x['reconcile_id'], self)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        context = self._context
        company_list = []
        ids = self.ids
        for line in self:
            if company_list and not line.company_id.id in company_list:
                raise Warning(_('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)
        for line in unrec_lines:
            if line.state != 'valid':
                raise Warning(_('Entry "%s" is not valid !') % line.name)
            credit += line['credit']
            debit += line['debit']
            currency += line['amount_currency'] or 0.0
            account_id = line['account_id']['id']
            partner_id = (line['partner_id'] and line['partner_id']['id']) or False
        writeoff = debit - credit

        # Ifdate_p in context => take this date
        if context.has_key('date_p') and context['date_p']:
            date=context['date_p']
        else:
            date = time.strftime('%Y-%m-%d')

        self._cr.execute('SELECT account_id, reconcile_id '\
                   'FROM account_move_line '\
                   'WHERE id IN %s '\
                   'GROUP BY account_id,reconcile_id',
                   (tuple(self.ids), ))
        r = self._cr.fetchall()
        #TODO: move this check to a constraint in the account_move_reconcile object
        if len(r) != 1:
            raise Warning(_('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise Warning(_('Entry is already reconciled.'))
        account = self.env['account.account'].browse(account_id)
        if not account.reconcile:
            raise Warning(_('The account is not defined to be reconciled !'))
        if r[0][1] != None:
            raise Warning(_('Some entries are already reconciled.'))

        if (not account.company_id.currency_id.is_zero(writeoff)) or \
           (account.currency_id and (not account.currency_id.is_zero(currency))):
            if not writeoff_acc_id:
                raise Warning(_('You have to provide an account for the write off/exchange difference entry.'))
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
                libelle = context['comment']
            else:
                libelle = _('Write-Off')

            cur_id = False
            amount_currency_writeoff = 0.0
            if context.get('company_currency_id',False) != context.get('currency_id',False):
                cur_id = context.get('currency_id',False)
                for line in unrec_lines:
                    if line.currency_id and line.currency_id.id == context.get('currency_id',False):
                        amount_currency_writeoff += line.amount_currency
                    else:
                        tmp_amount = line.account_id.company_id.currency_id.with_context({'date': line.date}).compute(context.get('currency_id',False), abs(line.debit-line.credit))
                        amount_currency_writeoff += (line.debit > 0) and tmp_amount or -tmp_amount

            writeoff_lines = [
                (0, 0, {
                    'name': libelle,
                    'debit': self_debit,
                    'credit': self_credit,
                    'account_id': account_id,
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and -1 * amount_currency_writeoff or (account.currency_id.id and -1 * currency or 0.0)
                }),
                (0, 0, {
                    'name': libelle,
                    'debit': debit,
                    'credit': credit,
                    'account_id': writeoff_acc_id,
                    'analytic_account_id': context.get('analytic_id', False),
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and amount_currency_writeoff or (account.currency_id.id and currency or 0.0)
                })
            ]

            
            writeoff_move_id = self.env['account.move'].create({
                'journal_id': writeoff_journal_id,
                'company_id': writeoff_journal_id and self.env['account.journal'].browse(writeoff_journal_id).company_id.id or False,
                'date': date,
                'state': 'draft',
                'line_id': writeoff_lines
            })

            writeoff_line_ids = self.search([('move_id', '=', writeoff_move_id.id), ('account_id', '=', account_id)]).ids
            if account_id == writeoff_acc_id:
                writeoff_line_ids = [writeoff_line_ids[1]]
            ids += writeoff_line_ids

        # marking the lines as reconciled does not change their validity, so there is no need
        # to revalidate their moves completely.
        reconcile_context = dict(context, novalidate=True)
        r_id = self.env['account.move.reconcile'].with_context(reconcile_context).create({
            'line_id': map(lambda x: (4, x, False), self.ids),
        })
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            workflow.trg_trigger(self._uid, 'account.move.line', id, self._cr)

        #To FIX: Here 'self.partner_id' doesn't work and it gives Expected singleton error.
        partner = self[0].partner_id
        if partner and not partner.has_something_to_reconcile():
            partner.mark_as_reconciled()
        return r_id

    @api.multi
    def _remove_move_reconcile(self):
        # Function remove move rencocile ids related with moves
        obj_move_rec = self.env['account.move.reconcile']
        unlink_ids = []
        if not self:
            return True
        full_recs = filter(lambda x: x.reconcile_id, self)
        rec_ids = [rec['reconcile_id'][0] for rec in full_recs]
        part_recs = filter(lambda x: x.reconcile_partial_id, self)
        part_rec_ids = [rec['reconcile_partial_id'][0] for rec in part_recs]
        unlink_ids += rec_ids
        unlink_ids += part_rec_ids
        all_moves = self.search(['|',('reconcile_id', 'in', unlink_ids),('reconcile_partial_id', 'in', unlink_ids)])
        all_moves = list(set(all_moves) - set(self))
        if unlink_ids:
            obj_move_rec.unlink(unlink_ids)
            if len(all_moves) >= 2:
                all_moves.reconcile_partial()
        return True

    @api.multi
    def unlink(self, check=True):
        self._update_check()
        result = False
        moves = set()
        context = dict(self._context or {})
        for line in self:
            moves.add(line.move_id)
            context['journal_id'] = line.journal_id.id
            context['date'] = line.date
            result = super(account_move_line, line).with_context(context).unlink()
        moves = list(moves)
        if check and moves:
            moves.with_context(context).validate()
        return result

    @api.multi
    def write(self, vals, check=True, update_check=True):
        if vals.get('account_tax_id', False):
            raise Warning(_('You cannot change the tax, you should remove and recreate lines.'))
        if ('account_id' in vals) and not self.env['account.account'].read(vals['account_id'], ['deprecated'])['deprecated']:
            raise Warning(_('You cannot use deprecated account.'))
        if update_check:
            if ('account_id' in vals) or ('journal_id' in vals) or ('date' in vals) or ('move_id' in vals) or ('debit' in vals) or ('credit' in vals) or ('date' in vals):
                self._update_check()

        todo_date = None
        if vals.get('date', False):
            todo_date = vals['date']
            del vals['date']

        for line in self:
            ctx = dict(self._context or {})
            if not ctx.get('journal_id'):
                if line.move_id:
                   ctx['journal_id'] = line.move_id.journal_id.id
                else:
                    ctx['journal_id'] = line.journal_id.id
            if not ctx.get('date'):
                if line.move_id:
                    ctx['date'] = line.move_id.date
                else:
                    ctx['date'] = line.date
        result = super(account_move_line, self).write(vals)
        if check:
            done = []
            for line in self:
                if line.move_id.id not in done:
                    done.append(line.move_id.id)
                    line.move_id.validate()
                    if todo_date:
                        line.move_id.write({'date': todo_date})
        return result

    @api.model
    def _update_journal_check(self, journal_id, date):
        #account_journal_period have been removed
#         self._cr.execute('SELECT state FROM account_journal_period WHERE journal_id = %s AND period_id = %s', (journal_id, period_id))
#         result = self._cr.fetchall()
#         journal = self.env['account.journal'].browse(journal_id)
#         period = self.env['account.period'].browse(period_id)
#         for (state,) in result:
#             if state == 'done':
#                 raise osv.except_osv(_('Error!'), _('You can not add/modify entries in a closed period %s of journal %s.' % (period.name,journal.name)))
#         if not result:
#             self.env['account.journal.period'].create({
#                 'name': (journal.code or journal.name)+':'+(period.name or ''),
#                 'journal_id': journal.id,
#                 'period_id': period.id
#             })
        return True

    @api.multi
    def _update_check(self):
        done = {}
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft' and (not line.journal_id.entry_posted):
                raise Warning(_('You cannot do this modification on a confirmed entry. You can just change some non legal fields or you must unconfirm the journal entry first.\n%s.') % err_msg)
            if line.reconcile_id:
                raise Warning(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            t = (line.journal_id.id, line.date)
            if t not in done:
                self._update_journal_check(line.journal_id.id, line.date)
                done[t] = True
        return True

    @api.model
    def create(self, vals, check=True):
        AccountObj = self.env['account.account']
        TaxObj = self.env['account.tax']
        MoveObj = self.env['account.move']
        context = dict(self._context or {})
        if vals.get('move_id', False):
            move = MoveObj.browse(vals['move_id'])
            if move.company_id:
                vals['company_id'] = move.company_id.id
            if move.date and not vals.get('date'):
                vals['date'] = move.date
        if ('account_id' in vals) and AccountObj.browse(vals['account_id']).deprecated:
            raise Warning(_('You cannot use deprecated account.'))
        if 'journal_id' in vals and vals['journal_id']:
            context['journal_id'] = vals['journal_id']
        if 'date' in vals and vals['date']:
            context['date'] = vals['date']
        if ('journal_id' not in context) and ('move_id' in vals) and vals['move_id']:
            m = MoveObj.browse(vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['date'] = m.date
        #we need to treat the case where a value is given in the context for period_id as a string
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        if 'date' not in context:
            context['date'] = fields.Date.context_today(self)
        self.with_context(context)._update_journal_check(context['journal_id'], context['date'])
        move_id = vals.get('move_id', False)
        journal = self.env['account.journal'].browse(context['journal_id'])
        vals['journal_id'] = vals.get('journal_id') or context.get('journal_id')
        vals['date'] = vals.get('date') or context.get('date')
        vals['date'] = vals.get('date') or context.get('date')
        if not move_id:
            if not vals.get('move_id', False):
                if journal.sequence_id:
                    #name = self.pool.get('ir.sequence').next_by_id(cr, uid, journal.sequence_id.id)
                    v = {
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'journal_id': context['journal_id']
                    }
                    if vals.get('ref', ''):
                        v.update({'ref': vals['ref']})
                    move_id = MoveObj.with_context(context).create(v)
                    vals['move_id'] = move_id.id
                else:
                    raise Warning(_('Cannot create an automatic sequence for this piece.\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.'))
        ok = not (journal.type_control_ids or journal.account_control_ids)
        if ('account_id' in vals):
            account = AccountObj.browse(vals['account_id'])
            if journal.type_control_ids:
                type = account.user_type
                for t in journal.type_control_ids:
                    if type.code == t.code:
                        ok = True
                        break
            if journal.account_control_ids and not ok:
                for a in journal.account_control_ids:
                    if a.id == vals['account_id']:
                        ok = True
                        break
            # Automatically convert in the account's secondary currency if there is one and
            # the provided values were not already multi-currency
            if account.currency_id and 'amount_currency' not in vals and account.currency_id.id != account.company_id.currency_id.id:
                vals['currency_id'] = account.currency_id.id
                ctx = {}
                if 'date' in vals:
                    ctx['date'] = vals['date']
                vals['amount_currency'] = account.company_id.currency_id.with_context(ctx).compute(
                    account.currency_id.id, vals.get('debit', 0.0) - vals.get('credit', 0.0))
        if not ok:
            raise Warning(_('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))
        result = super(account_move_line, self).create(vals)
        # CREATE Taxes
        if vals.get('account_tax_id', False):
            tax_id = TaxObj.browse(vals['account_tax_id'])
            total = vals['debit'] - vals['credit']
            base_code = 'base_code_id'
            tax_code = 'tax_code_id'
            account_id = 'account_collected_id'
            base_sign = 'base_sign'
            tax_sign = 'tax_sign'
            if journal.type in ('purchase_refund', 'sale_refund') or (journal.type in ('cash', 'bank') and total < 0):
                base_code = 'ref_base_code_id'
                tax_code = 'ref_tax_code_id'
                account_id = 'account_paid_id'
                base_sign = 'ref_base_sign'
                tax_sign = 'ref_tax_sign'
            tmp_cnt = 0
            for tax in TaxObj.compute_all([tax_id], total, 1.00, force_excluded=False).get('taxes'):
                #create the base movement
                if tmp_cnt == 0:
                    if tax[base_code]:
                        tmp_cnt += 1
                        if tax_id.price_include:
                            total = tax['price_unit']
                        newvals = {
                            'tax_code_id': tax[base_code],
                            'tax_amount': tax[base_sign] * abs(total),
                        }
                        if tax_id.price_include:
                            if tax['price_unit'] < 0:
                                newvals['credit'] = abs(tax['price_unit'])
                            else:
                                newvals['debit'] = tax['price_unit']
                        result.with_context(context).write(newvals)
                else:
                    data = {
                        'move_id': vals['move_id'],
                        'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                        'date': vals['date'],
                        'partner_id': vals.get('partner_id', False),
                        'ref': vals.get('ref', False),
                        'statement_id': vals.get('statement_id', False),
                        'account_tax_id': False,
                        'tax_code_id': tax[base_code],
                        'tax_amount': tax[base_sign] * abs(total),
                        'account_id': vals['account_id'],
                        'credit': 0.0,
                        'debit': 0.0,
                    }
                    if data['tax_code_id']:
                        self.with_context(context).create(data)
                #create the Tax movement
                data = {
                    'move_id': vals['move_id'],
                    'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                    'date': vals['date'],
                    'partner_id': vals.get('partner_id',False),
                    'ref': vals.get('ref',False),
                    'statement_id': vals.get('statement_id', False),
                    'account_tax_id': False,
                    'tax_code_id': tax[tax_code],
                    'tax_amount': tax[tax_sign] * abs(tax['amount']),
                    'account_id': tax[account_id] or vals['account_id'],
                    'credit': tax['amount']<0 and -tax['amount'] or 0.0,
                    'debit': tax['amount']>0 and tax['amount'] or 0.0,
                }
                if data['tax_code_id']:
                    self.with_context(context).create(data)
            del vals['account_tax_id']

        if check and not context.get('novalidate') and (context.get('recompute', True) or journal.entry_posted):
            move = MoveObj.browse(vals['move_id'])
            tmp = move.with_context(context).validate()
            if journal.entry_posted and tmp:
                move.with_context(context).button_validate()
        return result

    @api.model
    def list_journals(self):
        ng = dict(self.env['account.journal'].name_search('',[]))
        ids = ng.keys()
        result = []
        for journal in self.env['account.journal'].browse(ids):
            result.append((journal.id, ng[journal.id], journal.type, bool(journal.currency), bool(journal.analytic_journal_id)))
        return result
