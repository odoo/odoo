# -*- coding: utf-8 -*-

import time
from datetime import datetime

from openerp import workflow
from openerp import api, fields, models, _
from openerp.osv import osv, expression
from openerp.exceptions import RedirectWarning, Warning
import openerp.addons.decimal_precision as dp
from openerp import tools
from openerp.report import report_sxw
from openerp.tools import float_is_zero

class account_move_line(models.Model):
    _name = "account.move.line"
    _description = "Journal Item"
    _order = "date desc, id desc"

    @api.depends('debit', 'credit', 'amount_currency', 'currency_id',
        'reconcile_partial_ids.amount', 'reconcile_partial_with_ids.amount')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconciliable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconciliable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:

            amount = abs(line.debit - line.credit)
            sign = 1 if (line.debit - line.credit) > 0 else -1

            amount_residual_currency = abs(line.amount_currency) or 0.0
            digits_rounding_precision = line.currency_id.rounding if line.currency_id else line.company_id.currency_id.rounding

            for partial_line in (line.reconcile_partial_ids + line.reconcile_partial_with_ids):
                date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                amount -= partial_line.amount
                if line.currency_id:
                    if partial_line.currency_id and partial_line.currency_id == line.currency_id:
                        amount_residual_currency -= partial_line.amount_currency
                    elif partial_line.currency_id and partial_line.currency_id != line.currency_id:
                        amount_residual_currency -= line.currency_id.with_context(date=date).compute(partial_line.amount_currency, partial_line.currency_id)
                    else:
                        amount_residual_currency -= line.currency_id.with_context(date=date).compute(partial_line.amount, line.company_id.currency_id)

            line.amount_residual = amount*sign
            line.amount_residual_currency = amount_residual_currency*sign

            if float_is_zero(amount, digits_rounding_precision):
                line.reconciled = True
            else:
                line.reconciled = False

    @api.model
    def _get_currency(self):
        currency = False
        context = dict(self._context or {})
        if context.get('default_journal_id', False):
            currency = self.env['account.journal'].browse(context['default_journal_id']).currency
        return currency

    @api.model
    def _get_journal(self):
        """ Return journal based on the journal type """
        context = dict(self._context or {})
        journal_id = context.get('journal_id', False)
        if journal_id:
            return journal_id

        journal_type = context.get('journal_type', False)
        if journal_type:
            recs = self.env['account.journal'].search([('type','=',journal_type)])
            if not recs:
                action = self.env.ref('account.action_account_journal_form')
                msg = _("""Cannot find any account journal of "%s" type for this company, You should create one.\n Please go to Journal Configuration""") % journal_type.replace('_', ' ').title()
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            journal_id = recs[0].id
        return journal_id

    name = fields.Char(required=True)
    quantity = fields.Float(digits=(16,2),
        help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    debit = fields.Float(digits=0, default=0.0)
    credit = fields.Float(digits=0, default=0.0)
    amount_currency = fields.Float(string='Amount Currency', default=0.0,  digits=0,
        help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one('res.currency', string='Currency', default=_get_currency,
        help="The optional other currency if it is a multi-currency entry.")
    amount_residual = fields.Float(compute='_amount_residual', string='Residual Amount', store=True, digits=0,
        help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_currency = fields.Float(compute='_amount_residual', string='Residual Amount in Currency', store=True, digits=0,
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
        ondelete="cascade", domain=[('deprecated', '=', False)], default=lambda self: self._context.get('account_id', False))
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade",
        help="The move of this entry line.", index=True, required=True)
    narration = fields.Text(related='move_id.narration', string='Internal Note')
    ref = fields.Char(related='move_id.ref', string='Reference', store=True)
    statement_id = fields.Many2one('account.bank.statement', string='Statement',
        help="The bank statement used for bank reconciliation", index=True, copy=False)
    reconciled = fields.Boolean(compute='_amount_residual', store=True)
    reconcile_partial_with_ids = fields.One2many('account.partial.reconcile', 'credit_move_id', String='Partially Reconciled with',
        help='Moves in which this move is involved for partial reconciliation')
    reconcile_partial_ids = fields.One2many('account.partial.reconcile', 'debit_move_id', String='Partial Reconciliation',
        help='Moves involved in this move partial reconciliation')
    journal_id = fields.Many2one('account.journal', related='move_id.journal_id', string='Journal',
        default=_get_journal, required=True, index=True, store=True)
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")
    date_maturity = fields.Date(string='Due date', index=True ,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    date = fields.Date(related='move_id.date', string='Effective date', required=True, index=True, default=fields.Date.context_today, store=True)
    analytic_lines = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines')
    tax_ids = fields.Many2many('account.tax', string='Taxes', copy=False, readonly=True)
    tax_line_id = fields.Many2one('account.tax', string='Originator tax', copy=False, readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    company_id = fields.Many2one('res.company', related='account_id.company_id', string='Company', store=True,
        default=lambda self: self.env['res.company']._company_default_get('account.move.line'))

    # TODO: put the invoice link and partner_id on the account_move
    invoice = fields.Many2one('account.invoice', string='Invoice')
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, ondelete='restrict')

    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    @api.multi
    @api.constrains('account_id')
    def _check_account_type(self):
        for line in self:
            if line.account_id.internal_type == 'consolidation':
                raise Warning(_('You cannot create journal items on an account of type consolidation.'))

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
                raise Warning(_("You cannot create journal items with a secondary currency without filling both 'currency' and 'amount currency' field."))

    @api.multi
    @api.constrains('amount_currency')
    def _check_currency_amount(self):
        for line in self:
            if line.amount_currency:
                if (line.amount_currency > 0.0 and line.credit > 0.0) or (line.amount_currency < 0.0 and line.debit > 0.0):
                    raise Warning(_('The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.'))


    ####################################################
    # Reconciliation interface methods
    ####################################################

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_id=None):
        """ Returns the data required for the  manual reconciliation of partners/accounts.
            If no res_id is passed, returns data for all partners/accounts that can be reconciled.

            :param res_type: either 'partner' or 'account'
            :param res_id: id of the partner/account to reconcile
        """
        is_partner = res_type == 'partner'
        res_alias = is_partner and 'p' or 'a'
        self.env.cr.execute(
            """ SELECT %s account_id, account_name, account_code, max_date, to_char(last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked FROM (
                    SELECT %s
                        %s.last_time_entries_checked AS last_time_entries_checked,
                        a.id AS account_id,
                        a.name AS account_name,
                        a.code AS account_code,
                        MAX(l.write_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a ON (a.id = l.account_id)
                        RIGHT JOIN account_account_type at ON (at.id = a.user_type)
                        %s
                    WHERE
                        a.reconcile IS TRUE
                        %s
                        %s
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            %s
                            AND l.amount_residual > 0
                        )
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            %s
                            AND l.amount_residual < 0
                        )
                    GROUP BY %s a.id, a.name, a.code, %s.last_time_entries_checked
                    ORDER BY %s.last_time_entries_checked
                ) as s
                WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
            """ % (
                is_partner and 'partner_id, partner_name,' or ' ',
                is_partner and 'p.id AS partner_id, p.name AS partner_name,' or ' ',
                res_alias,
                is_partner and 'RIGHT JOIN res_partner p ON (l.partner_id = p.id)' or ' ',
                is_partner and ' ' or "AND at.type <> 'payable' AND at.type <> 'receivable'",
                res_id and 'AND '+res_alias+'.id = '+str(res_id) or '',
                is_partner and 'AND l.partner_id = p.id' or ' ',
                is_partner and 'AND l.partner_id = p.id' or ' ',
                is_partner and 'l.partner_id, p.id,' or ' ',
                res_alias,
                res_alias,
            ))

        # Apply ir_rules by filtering out
        rows = self.env.cr.dictfetchall()
        ids = [x['account_id'] for x in rows]
        allowed_ids = set(self.env['account.account'].browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]
        if is_partner:
            ids = [x['partner_id'] for x in rows]
            allowed_ids = set(self.env['res.partner'].browse(ids).ids)
            rows = [row for row in rows if row['partner_id'] in allowed_ids]

        # Fetch other data
        for row in rows:
            account = self.env['account.account'].browse(row['account_id'])
            row['currency_id'] = account.currency_id.id or account.company_id.currency_id.id
            partner_id = is_partner and row['partner_id'] or None
            row['reconciliation_proposition'] = self.get_reconciliation_proposition(account.id, partner_id)

        return rows

    @api.model
    def get_reconciliation_proposition(self, account_id, partner_id=False):
        """ Returns two lines whose amount are opposite """

        # Get pairs
        partner_id_condition = partner_id and 'AND a.partner_id = %d AND b.partner_id = %d' % (partner_id, partner_id) or ''
        self.env.cr.execute(
            """ SELECT a.id, b.id
                FROM account_move_line a, account_move_line b
                WHERE a.amount_residual = - b.amount_residual
                AND NOT a.reconciled AND NOT b.reconciled
                AND a.account_id = %d AND b.account_id = %d
                %s
                ORDER BY a.date asc
                LIMIT 10
            """ % (account_id, account_id, partner_id_condition))
        pairs = self.env.cr.fetchall()

        # Apply ir_rules by filtering out
        all_pair_ids = [element for tupl in pairs for element in tupl]
        allowed_ids = set(self.env['account.move.line'].browse(all_pair_ids).ids)
        pairs = [pair for pair in pairs if pair[0] in allowed_ids and pair[1] in allowed_ids]

        # Return lines formatted
        if len(pairs) > 0:
            target_currency = self.currency_id or self.company_id.currency_id
            lines = self.browse(list(pairs[0]))
            return lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)
        else:
            return []

    @api.model
    def domain_move_lines_for_reconciliation(self, excluded_ids=None, str=False):
        """ Returns the domain which is common to both manual and bank statement reconciliation.

            :param excluded_ids: list of ids of move lines that should not be fetched
            :param str: search string
        """
        context = (self._context or {})
        if excluded_ids is None:
            excluded_ids = []
        domain = []

        if excluded_ids:
            domain = expression.AND([domain, [('id', 'not in', excluded_ids)]])
        if str:
            str_domain = [
                '|', ('move_id.name', 'ilike', str),
                '|', ('move_id.ref', 'ilike', str),
                '|', ('date_maturity', 'like', str),
                '&', ('name', '!=', '/'), ('name', 'ilike', str)
            ]
            try:
                amount = float(str)
                amount_domain = ['|', ('amount_residual', '=', amount), '|', ('amount_residual_currency', '=', amount), '|', ('amount_residual', '=', -amount), ('amount_residual_currency', '=', -amount)]
                str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass

            # Warning : this is undue coupling. But building this domain is really tricky.
            # What follows means : "If building a domain for the bank statement reconciliation, id there's no partner
            # and a search string, we want to find the string in any of those fields including the partner name
            if 'bank_statement_line' in context and not context['bank_statement_line'].partner_id.id:
                str_domain = expression.OR([str_domain, [('partner_id.name', 'ilike', str)]])

            domain = expression.AND([domain, str_domain])

        return domain

    def _domain_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, str=False):
        """ Create domain criteria that are relevant to manual reconciliation. """
        domain = ['&', ('reconciled', '=', False), ('account_id', '=', account_id)]
        if partner_id:
            domain = expression.AND([domain, [('partner_id','=',partner_id)]])
        generic_domain = self.domain_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str)

        return expression.AND([generic_domain, domain])

    @api.model
    def get_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, str=False, offset=0, limit=None, target_currency_id=False):
        """ Returns unreconciled move lines for an account or a partner+account, formatted for the manual reconciliation widget """
        domain = self._domain_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, str)
        lines = self.search(domain, offset=offset, limit=limit, order="date_maturity asc, id asc")
        if target_currency_id:
            target_currency = self.env['res.currency'].browse(target_currency_id)
        else:
            account = self.env['account.account'].browse(account_id)
            target_currency = account.currency_id or account.company_id.currency_id
        return lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)

    @api.v7
    def prepare_move_lines_for_reconciliation_widget(self, cr, uid, line_ids, target_currency_id=False, context=None):
        target_currency = target_currency_id and self.pool.get('res.currency').browse(cr, uid, target_currency_id, context=context) or False
        return self.browse(cr, uid, line_ids, context).prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)

    @api.v8
    def prepare_move_lines_for_reconciliation_widget(self, target_currency=False, target_date=False):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param target_currency: curreny you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        context = dict(self._context or {})
        company_currency = self.env.user.company_id.currency_id
        rml_parser = report_sxw.rml_parse(self._cr, self._uid, 'reconciliation_widget_aml', context=self._context)
        ret = []

        for line in self:
            ret_line = {
                'id': line.id,
                'name': line.name if line.name != '/' else line.move_id.name,
                'ref': line.move_id.ref,
                # for reconciliation with existing entries (eg. cheques)
                # NB : we don't use the 'reconciled' field because the line we're selecting is not the one that gets reconciled
                'is_reconciled': not line.account_id.reconcile,
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.internal_type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'journal_name': line.journal_id.name,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'is_partially_reconciled': bool(line.reconcile_partial_ids),
                'currency_id': line.currency_id.id or False,
            }

            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency

            # For already reconciled lines, don't use amount_residual(_currency)
            if not line.account_id.reconcile:
                amount = debit - credit
                amount_currency = line.amount_currency

            # Get right debit / credit:
            target_currency = target_currency or company_currency
            line_currency = line.currency_id or company_currency
            amount_currency_str = ""
            total_amount_currency_str = ""
            if line_currency != company_currency:
                total_amount = line.amount_currency
                actual_debit = debit > 0 and amount_currency or 0.0
                actual_credit = credit > 0 and -amount_currency or 0.0
            else:
                total_amount = abs(debit - credit)
                actual_debit = debit > 0 and amount or 0.0
                actual_credit = credit > 0 and -amount or 0.0
            if line_currency != target_currency:
                amount_currency_str = rml_parser.formatLang(actual_debit or actual_credit, currency_obj=line_currency)
                total_amount_currency_str = rml_parser.formatLang(total_amount, currency_obj=line_currency)
                ret_line['credit_currency'] = actual_credit
                ret_line['debit_currency'] = actual_debit
                ctx = context.copy()
                if target_date:
                    ctx.update({'date': target_date})
                total_amount = line_currency.with_context(ctx).compute(total_amount, target_currency)
                actual_debit = line_currency.with_context(ctx).compute(actual_debit, target_currency)
                actual_credit = line_currency.with_context(ctx).compute(actual_credit, target_currency)
            amount_str = rml_parser.formatLang(actual_debit or actual_credit, currency_obj=target_currency)
            total_amount_str = rml_parser.formatLang(total_amount, currency_obj=target_currency)

            ret_line['debit'] = actual_debit
            ret_line['credit'] = actual_credit
            ret_line['amount_str'] = amount_str
            ret_line['total_amount_str'] = total_amount_str
            ret_line['amount_currency_str'] = amount_currency_str
            ret_line['total_amount_currency_str'] = total_amount_currency_str
            ret.append(ret_line)
        return ret

    @api.v7
    def process_reconciliations(self, cr, uid, data, context=None):
        """ Used to validate a batch of reconciliations in a single call

            :param data: list of dicts containing:
                - 'type': either 'partner' or 'account'
                - 'id': id of the affected res.partner or account.account
                - 'mv_line_ids': ids of exisiting account.move.line to reconcile
                - 'new_mv_line_dicts': list of dicts containing values suitable for account_move_line.create()
        """
        for datum in data:
            if len(datum['mv_line_ids']) >= 1 or len(datum['mv_line_ids']) + len(datum['new_mv_line_dicts']) >= 2:
                self.process_reconciliation(cr, uid, datum['mv_line_ids'], datum['new_mv_line_dicts'], context=context)
        
            if datum['type'] == 'partner':
                self.env['res.partner'].browse(datum['id']).mark_as_reconciled()
            if datum['type'] == 'account':
                self.env['account.account'].browse(datum['id']).mark_as_reconciled()

    @api.v7
    def process_reconciliation(self, cr, uid, mv_line_ids, new_mv_line_dicts, context=None):
        return self.browse(cr, uid, mv_line_ids, context).process_reconciliation(new_mv_line_dicts)

    @api.v8
    def process_reconciliation(self, new_mv_line_dicts):
        """ Create new move lines from new_mv_line_dicts (if not empty) then call reconcile_partial on self and new move lines

            :param new_mv_line_dicts: list of dicts containing values suitable fot account_move_line.create()
        """
        if len(self) < 1 or len(self) + len(new_mv_line_dicts) < 2:
            raise Warning(_('Error!'), _('A reconciliation must involve at least 2 move lines.'))
        
        # Create writeoff move lines
        if len(new_mv_line_dicts) > 0:
            writeoff_lines = self.env['account.move.line']
            company_currency = self[0].account_id.company_id.currency_id
            account_currency = self[0].account_id.currency_id or company_currency
            for mv_line_dict in new_mv_line_dicts:
                if account_currency != company_currency:
                    mv_line_dict['debit'] = account_currency.compute(mv_line_dict['debit'], company_currency)
                    mv_line_dict['credit'] = account_currency.compute(mv_line_dict['credit'], company_currency)
                    amount_currency = mv_line_dict['debit'] - mv_line_dict['credit']
                writeoff_lines += self._create_writeoff(mv_line_dict)
            
            (self+writeoff_lines).reconcile()
        else:
            self.reconcile()


    ####################################################
    # Reconciliation methods
    ####################################################

    def _get_pair_to_reconcile(self):
        #target the pair of move in self with smallest debit, credit
        smallest_debit = smallest_credit = False
        for aml in self:
            if aml.amount_residual > 0:
                smallest_debit = (not smallest_debit or aml.amount_residual < smallest_debit.amount_residual) and aml or smallest_debit
            elif aml.amount_residual < 0:
                smallest_credit = (not smallest_credit or aml.amount_residual > smallest_credit.amount_residual) and aml or smallest_credit
        return smallest_debit, smallest_credit

    def auto_reconcile_lines(self):
        """ This function iterates recursively on the recordset given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process
        """
        sm_debit_move, sm_credit_move = self._get_pair_to_reconcile()
        #there is no more pair to reconcile so return what move_line are left
        if not sm_credit_move or not sm_debit_move:
            return self

        #Reconcile the pair together
        amount_reconcile = min(sm_debit_move.amount_residual, -sm_credit_move.amount_residual)
        #Remove from recordset the one(s) that will be totally reconciled
        if amount_reconcile == sm_debit_move.amount_residual:
            self -= sm_debit_move
        if amount_reconcile == sm_credit_move.amount_residual:
            self -= sm_credit_move

        #Check for currency
        currency = False
        amount_reconcile_currency = 0
        if sm_debit_move.currency_id == sm_credit_move.currency_id:
            currency = sm_credit_move.currency_id
            amount_reconcile_currency = min(sm_debit_move.amount_residual_currency, -sm_credit_move.amount_residual_currency)

        self.env['account.partial.reconcile'].create({'debit_move_id': sm_debit_move.id, 
            'credit_move_id': sm_credit_move.id, 
            'amount': amount_reconcile,
            'amount_currency': amount_reconcile_currency,
            'currency_id': currency and currency.id or False,})

        #Iterate process again on self
        return self.auto_reconcile_lines()

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        #Perform all checks on lines
        company_ids = []
        all_accounts = []
        partners = []
        for move in self:
            company_ids.append(move.company_id.id)
            all_accounts.append(move.account_id)
            if (move.account_id.internal_type in ('receivable', 'payable')):
                partners.append(move.partner_id.id)
            if move.reconciled:
                raise Warning(_('You are trying to reconcile some entries that are already reconciled!'))

        if len(set(company_ids)) > 1:
            raise Warning(_('To reconcile the entries company should be the same for all entries!'))
        if len(set(all_accounts)) > 1:
            raise Warning(_('Entries are not of the same account!'))
        if not all_accounts[0].reconcile:
            raise Warning(_('The account %s (%s) is not marked as reconciliable !') % (all_accounts[0].name, all_accounts[0].code))
        if len(set(partners)) > 1:
            raise Warning(_('The partner has to be the same on all lines for receivable and payable accounts!'))

        #reconcile everything that can be
        remaining_moves = self.auto_reconcile_lines()
        
        #if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            writeoff_to_reconcile = remaining_moves._create_writeoff({'account_id': writeoff_acc_id.id, 'journal_id': writeoff_journal_id.id})
            #add writeoff line to reconcile algo and finish the reconciliation
            remaining_moves = (remaining_moves+writeoff_to_reconcile).auto_reconcile_lines()

    def _create_writeoff(self, vals):
        """ Create a writeoff move for the account.move.lines in self. If debit/credit is not specified in vals, 
            
            :param vals: dict containing values suitable fot account_move_line.create(). The data in vals will
                be processed to create bot writeoff acount.move.line and their enclosing account.move.
        """
        # Check and complete vals
        if not 'account_id' in vals or not 'journal_id' in vals:
            raise Warning("It is mandatory to specify an account and a journal to create a write-off.")
        if ('debit' in vals) ^ ('credit' in vals):
            raise Warning("Either pass both debit and credit or none.")
        company_currency = self[0].account_id.company_id.currency_id
        account_currency = self[0].account_id.currency_id or company_currency
        if not 'credit' in vals and not 'debit' in vals:
            amount = sum([r.amount_residual for r in self])
            vals['debit'] = amount > 0 and amount or 0.0
            vals['credit'] = amount < 0 and abs(amount) or 0.0
        if not 'account_currency' in vals and account_currency != company_currency:
            vals['currency_id'] = account_currency
            vals['amount_currency'] = sum([r.amount_residual_currency for r in self])
        if not 'date' in vals:
            vals['date'] = self._context.get('date_p') or time.strftime('%Y-%m-%d')
        if not 'name' in vals:
            vals['name'] = self._context.get('comment') or _('Write-Off')

        # Writeoff line in the account of self
        first_line_dict = vals.copy()
        first_line_dict['account_id'] = self[0].account_id.id
        first_line_dict['partner_id'] = self[0].partner_id.id
        if 'analytic_account_id' in vals:
            del vals['analytic_account_id']

        # Writeoff line in specified writeoff account
        second_line_dict = vals.copy()
        second_line_dict['debit'], second_line_dict['credit'] = second_line_dict['credit'], second_line_dict['debit']
        if 'amount_currency' in vals:
            second_line_dict['amount_currency'] = - second_line_dict['amount_currency']
        
        # Create the move
        writeoff_move = self.env['account.move'].create({
            'journal_id': vals['journal_id'],
            'company_id': self.env['account.journal'].browse(vals['journal_id']).company_id.id,
            'date': vals['date'],
            'state': 'draft',
            'line_id': [(0, 0, first_line_dict), (0, 0, second_line_dict)],
        })

        # Return the writeoff move.line which is to be reconciled
        line = writeoff_move.line_id.filtered(lambda r: r.account_id == self[0].account_id)
        if line:
            return line
        else:
            raise osv.except_osv(_('Programming Error'), _('Writeoff improperly created.'))

    @api.multi
    def remove_move_reconcile(self):
        if not self:
            return True
        rec_move_ids = self.env['account.partial.reconcile']
        for account_move_line in self:
            rec_move_ids += account_move_line.reconcile_partial_ids
            rec_move_ids += account_move_line.reconcile_partial_with_ids
        return rec_move_ids.unlink()


    ####################################################
    # CRUD methods
    ####################################################

    @api.model
    def create(self, vals, check=True):
        AccountObj = self.env['account.account']
        TaxObj = self.env['account.tax']
        MoveObj = self.env['account.move']
        context = dict(self._context or {})
        amount = vals.get('debit', 0.0) - vals.get('credit', 0.0)

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
                vals['amount_currency'] = account.company_id.currency_id.with_context(ctx).compute(amount, account.currency_id)
        if not ok:
            raise Warning(_('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

        # WIP
        # Create tax lines
        # if not context.get("dont_create_taxes") and vals.get('tax_ids') and vals['tax_ids']:
            # Since create() receives ids instead of recordset, let's just use the old-api bridge
            # taxes = TaxObj.compute_all(self._cr, self._uid, vals['tax_ids'], amount, vals.get('currency_id', None), 1, vals.get('product_id', None), vals.get('partner_id', None), context=context)['taxes']
            # for vals in self.get_tax_move_lines(taxes):
                # super(account_move_line, self).create(vals)

        result = super(account_move_line, self).create(vals)

        if check and not context.get('novalidate') and (context.get('recompute', True) or journal.entry_posted):
            move = MoveObj.browse(vals['move_id'])
            # TODO: FIX ME
            # move.with_context(context)._post_validate()
            if journal.entry_posted:
                move.with_context(context).button_validate()
        return result

    @api.multi
    def unlink(self, check=True):
        self._update_check()
        result = False
        moves = self.env['account.move']
        context = dict(self._context or {})
        for line in self:
            moves += line.move_id
            context['journal_id'] = line.journal_id.id
            context['date'] = line.date
            line.with_context(context)
            result = super(account_move_line, line).unlink()
        if check and moves:
            moves.with_context(context)._post_validate()
        return result

    @api.multi
    def write(self, vals, check=True, update_check=True):
        if vals.get('tax_line_id') or vals.get('tax_ids'):
            raise Warning(_('You cannot change the tax, you should remove and recreate lines.'))
        if ('account_id' in vals) and self.env['account.account'].browse(vals['account_id']).deprecated:
            raise Warning(_('You cannot use deprecated account.'))
        if update_check and any(key in vals for key in ('account_id', 'journal_id', 'date', 'move_id', 'debit', 'credit')):
            self._update_check()

        # Check for centralisation
        # TODO : what happened with journal.centralisation ?
        # for line in self:
        #     journal = line.move_id and line.move_id.journal_id or line.journal_id
        #     journal = self._context.get('journal_id') and self.env['account.journal'].browse(self._context.get('journal_id')) or journal # Legacy
        #     if journal.centralisation:
        #         pass
        #         # Do something here

        todo_date = vals.pop('date', False)
        result = super(account_move_line, self).write(vals)
        if check:
            done = []
            for line in self:
                if line.move_id.id not in done:
                    done.append(line.move_id.id)
                    line.move_id._post_validate()
                    if todo_date:
                        line.move_id.write({'date': todo_date})
        return result

    @api.multi
    def _update_check(self):
        """ Raise Warning to cause rollback if self is in a correct state """
        done = {}
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft' and (not line.journal_id.entry_posted):
                raise Warning(_('You cannot do this modification on a confirmed entry. You can just change some non legal fields or you must unconfirm the journal entry first.\n%s.') % err_msg)
            if line.reconciled:
                raise Warning(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            t = (line.journal_id.id, line.date)
            if t not in done:
                self._update_journal_check(line.journal_id.id, line.date)
                done[t] = True
        return True

    @api.model
    def _update_journal_check(self, journal_id, date):
        # TODO : since account_journal_period have been removed, how to check date is not in a closed period ?
        # self._cr.execute('SELECT state FROM account_journal_period WHERE journal_id = %s AND period_id = %s', (journal_id, period_id))
        # result = self._cr.fetchall()
        # journal = self.env['account.journal'].browse(journal_id)
        # period = self.env['account.period'].browse(period_id)
        # for (state,) in result:
        #     if state == 'done':
        #         raise osv.except_osv(_('Error!'), _('You can not add/modify entries in a closed period %s of journal %s.' % (period.name,journal.name)))
        # if not result:
        #     self.env['account.journal.period'].create({
        #         'name': (journal.code or journal.name)+':'+(period.name or ''),
        #         'journal_id': journal.id,
        #         'period_id': period.id
        #     })
        return True


    ####################################################
    # Misc / utility methods
    ####################################################

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

    @api.model
    def compute_amount_fields(self, amount, src_currency, company_currency):
        """ Compute value for fields debit/credit/amount_currency """
        amount_currency = False
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = src_currency.compute(amount, company_currency)
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        return debit, credit, amount_currency

    @api.multi
    def create_analytic_lines(self):
        for obj_line in self:
            if obj_line.analytic_account_id:
                if not obj_line.journal_id.analytic_journal_id:
                    raise Warning(_("You have to define an analytic journal on the '%s' journal!") % (obj_line.journal_id.name, ))
                if obj_line.analytic_lines:
                    obj_line.analytic_lines.unlink()
                vals_line = self._prepare_analytic_line(obj_line)
                self.env['account.analytic.line'].create(vals_line)

    @api.model
    def _prepare_analytic_line(self, obj_line):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.

            :param obj_line: browse record of the account.move.line that triggered the analytic line creation
        """
        return {
            'name': obj_line.name,
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

    @api.model
    def _query_get(self, obj='l'):
        """ Build SQL query to fetch lines based on obj and context """

        fiscalyear_obj = self.env['account.fiscalyear']
        account_obj = self.env['account.account']
        fiscalyear_ids = []
        context = dict(self._context or {})
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        query = ''
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
            if child_ids:
                query += ' AND '+obj+'.account_id IN (%s)' % ','.join(map(str, child_ids))

        query += company_clause
        return query


class account_partial_reconcile(models.Model):
    _name = "account.partial.reconcile"
    _description = "Partial Reconcile"

    debit_move_id = fields.Many2one('account.move.line')
    credit_move_id = fields.Many2one('account.move.line')
    amount = fields.Float()
    amount_currency = fields.Float()
    currency_id = fields.Many2one('res.currency', string='Currency')
