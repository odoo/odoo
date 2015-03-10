# -*- coding: utf-8 -*-

import time
from openerp import api, fields, models, _
from openerp.osv import osv, expression
from openerp.exceptions import RedirectWarning, UserError
from openerp.report import report_sxw
from openerp.tools import float_is_zero
from openerp.tools.safe_eval import safe_eval


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _description = "Journal Item"
    _order = "date desc, id desc"

    @api.depends('debit', 'credit', 'amount_currency', 'currency_id', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'account_id.currency_id')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconciliable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconciliable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            #amounts in the partial reconcile table aren't signed, so we need to use abs()
            amount = abs(line.debit - line.credit)
            amount_residual_currency = abs(line.amount_currency) or 0.0
            sign = 1 if (line.debit - line.credit) > 0 else -1

            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                amount -= partial_line.amount
                #getting the date of the matched item to compute the amount_residual in currency
                date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                if line.currency_id:
                    if partial_line.currency_id and partial_line.currency_id == line.currency_id:
                        amount_residual_currency -= partial_line.amount_currency
                    else:
                        amount_residual_currency -= line.company_id.currency_id.with_context(date=date).compute(partial_line.amount, line.currency_id)

            #computing the `reconciled` field. As we book exchange rate difference on each partial matching,
            #we can only check the amount in company currency
            reconciled = False
            digits_rounding_precision = line.company_id.currency_id.rounding
            if float_is_zero(amount, digits_rounding_precision):
                reconciled = True
            line.reconciled = reconciled

            line.amount_residual = line.company_id.currency_id.round(amount * sign)
            line.amount_residual_currency = line.currency_id and line.currency_id.round(amount_residual_currency * sign) or 0.0

    @api.depends('debit', 'credit')
    def _store_balance(self):
        for line in self:
            line.balance = line.debit - line.credit

    @api.model
    def _get_currency(self):
        currency = False
        context = self._context or {}
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
            recs = self.env['account.journal'].search([('type', '=', journal_type)])
            if not recs:
                action = self.env.ref('account.action_account_journal_form')
                msg = _("""Cannot find any account journal of "%s" type for this company, You should create one.\n Please go to Journal Configuration""") % journal_type.replace('_', ' ').title()
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            journal_id = recs[0].id
        return journal_id

    @api.depends('debit', 'credit', 'move_id.matched_percentage', 'move_id.journal_id')
    def _compute_cash_basis(self):
        for move_line in self:
            if move_line.journal_id.type in ('sale', 'purchase'):
                move_line.debit_cash_basis = move_line.debit * move_line.move_id.matched_percentage
                move_line.credit_cash_basis = move_line.credit * move_line.move_id.matched_percentage
            else:
                move_line.debit_cash_basis = move_line.debit
                move_line.credit_cash_basis = move_line.credit
            move_line.balance_cash_basis = move_line.debit_cash_basis - move_line.credit_cash_basis

    name = fields.Char(required=True)
    quantity = fields.Float(digits=(16, 2),
        help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    debit_cash_basis = fields.Float('Debit with cash basis method', default=0.0)
    credit_cash_basis = fields.Float('Credit with cash basis method', default=0.0)
    debit = fields.Float(digits=0, default=0.0)
    credit = fields.Float(digits=0, default=0.0)
    balance = fields.Float(compute='_store_balance', store=True, digits=0, default=0.0, help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    debit_cash_basis = fields.Float(digits=0, default=0.0, compute='_compute_cash_basis', store=True)
    credit_cash_basis = fields.Float(digits=0, default=0.0, compute='_compute_cash_basis', store=True)
    balance_cash_basis = fields.Float(compute='_compute_cash_basis', store=True, digits=0, default=0.0, help="Technical field holding the debit_cash_basis - credit_cash_basis in order to open meaningful graph views from reports")
    amount_currency = fields.Float(default=0.0, digits=0,
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
    ref = fields.Char(related='move_id.ref', string='Reference', store=True, copy=False)
    statement_id = fields.Many2one('account.bank.statement', string='Statement',
        help="The bank statement used for bank reconciliation", index=True, copy=False)
    reconciled = fields.Boolean(compute='_amount_residual', store=True)
    matched_debit_ids = fields.One2many('account.partial.reconcile', 'credit_move_id', String='Matched Debits',
        help='Debit journal items that are matched with this journal item.')
    matched_credit_ids = fields.One2many('account.partial.reconcile', 'debit_move_id', String='Matched Credits',
        help='Credit journal items that are matched with this journal item.')
    journal_id = fields.Many2one('account.journal', related='move_id.journal_id', string='Journal',
        default=_get_journal, required=True, index=True, store=True, copy=False)
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")
    date_maturity = fields.Date(string='Due date', index=True,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    date = fields.Date(related='move_id.date', string='Effective date', required=True, index=True, default=fields.Date.context_today, store=True, copy=False)
    analytic_lines = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines')
    tax_ids = fields.Many2many('account.tax', string='Taxes', copy=False, readonly=True)
    tax_line_id = fields.Many2one('account.tax', string='Originator tax', copy=False, readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    company_id = fields.Many2one('res.company', related='account_id.company_id', string='Company', store=True,
        default=lambda self: self.env['res.company']._company_default_get('account.move.line'))

    # TODO: put the invoice link and partner_id on the account_move
    invoice = fields.Many2one('account.invoice')
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, ondelete='restrict')
    user_type = fields.Many2one('account.account.type', related='account_id.user_type', index=True, store=True)

    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)', 'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    def compute_fields(self, field_names):
        if len(self) == 0:
            return []
        select = ','.join(['\"account_move_line\".' + k + (self.env.context.get('cash_basis') and '_cash_basis' or '') for k in field_names])
        where_clause, where_params = self._query_get()
        sql = "SELECT \"account_move_line\".id," + select + " FROM \"account_move_line\" WHERE " + where_clause + " AND \"account_move_line\".id IN %s GROUP BY \"account_move_line\".id"

        where_params += [tuple(self.ids)]
        self.env.cr.execute(sql, where_params)
        results = self.env.cr.fetchall()
        results = dict([(k[0], k[1:]) for k in results])
        for id, l in results.items():
            results[id] = dict([(field_names[i], k) for i, k in enumerate(l)])
        return results

    @api.multi
    @api.constrains('account_id')
    def _check_account_type(self):
        for line in self:
            if line.account_id.internal_type == 'consolidation':
                raise UserError(_('You cannot create journal items on an account of type consolidation.'))

    @api.multi
    @api.constrains('currency_id')
    def _check_currency(self):
        for line in self:
            if line.account_id.currency_id:
                if not line.currency_id or not line.currency_id.id == line.account_id.currency_id.id:
                    raise UserError(_('The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account or select a multi-currency view on the journal.'))

    @api.multi
    @api.constrains('currency_id', 'amount_currency')
    def _check_currency_and_amount(self):
        for line in self:
            if (line.amount_currency and not line.currency_id):
                raise UserError(_("You cannot create journal items with a secondary currency without filling both 'currency' and 'amount currency' field."))

    @api.multi
    @api.constrains('amount_currency')
    def _check_currency_amount(self):
        for line in self:
            if line.amount_currency:
                if (line.amount_currency > 0.0 and line.credit > 0.0) or (line.amount_currency < 0.0 and line.debit > 0.0):
                    raise UserError(_('The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.'))

    ####################################################
    # Reconciliation interface methods
    ####################################################

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_id=None):
        """ Returns the data required for the invoices & payments matching of partners/accounts.
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
                res_id and 'AND ' + res_alias + '.id = ' + str(res_id) or '',
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
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])
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
        # TODO : what about multicompany ? shouldn't it be sth like self and self[0].account_id.company_id.currency_id ?
        company_currency = self.env.user.company_id.currency_id
        rml_parser = report_sxw.rml_parse(self._cr, self._uid, 'reconciliation_widget_aml', context=self._context)
        ret = []

        for line in self:
            ret_line = {
                'id': line.id,
                'name': line.name != '/' and line.move_id.name + ': ' + line.name or line.move_id.name,
                'ref': line.move_id.ref or '',
                # For reconciliation between statement transactions and already registered payments (eg. checks)
                # NB : we don't use the 'reconciled' field because the line we're selecting is not the one that gets reconciled
                'already_paid': line.account_id.internal_type == 'liquidity',
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.internal_type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'journal_name': line.journal_id.name,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                #'is_partially_reconciled': bool(line.reconcile_partial_ids),
                #TODO: use 'reconciled_percentage' field
                'currency_id': line.currency_id.id or False,
            }

            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency

            # For already reconciled lines, don't use amount_residual(_currency)
            if line.account_id.internal_type == 'liquidity':
                amount = abs(debit - credit)
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
            raise UserError(_('Error!'), _('A reconciliation must involve at least 2 move lines.'))

        # Create writeoff move lines
        if len(new_mv_line_dicts) > 0:
            writeoff_lines = self.env['account.move.line']
            company_currency = self[0].account_id.company_id.currency_id
            account_currency = self[0].account_id.currency_id or company_currency
            for mv_line_dict in new_mv_line_dicts:
                if account_currency != company_currency:
                    mv_line_dict['debit'] = account_currency.compute(mv_line_dict['debit'], company_currency)
                    mv_line_dict['credit'] = account_currency.compute(mv_line_dict['credit'], company_currency)
                writeoff_lines += self._create_writeoff(mv_line_dict)

            (self + writeoff_lines).reconcile()
        else:
            self.reconcile()

    ####################################################
    # Reconciliation methods
    ####################################################

    def _get_pair_to_reconcile(self):
        #field is either 'amount_residual' or 'amount_residual_currency' (if the reconciled account has a secondary currency set)
        field = self[0].account_id.currency_id and 'amount_residual_currency' or 'amount_residual'
        #target the pair of move in self with smallest debit, credit
        smallest_debit = smallest_credit = False
        for aml in self:
            if aml[field] > 0:
                smallest_debit = (not smallest_debit or aml[field] < smallest_debit[field]) and aml or smallest_debit
            elif aml[field] < 0:
                smallest_credit = (not smallest_credit or aml[field] > smallest_credit[field]) and aml or smallest_credit
        return smallest_debit, smallest_credit

    def auto_reconcile_lines(self):
        """ This function iterates recursively on the recordset given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        if not self.ids:
            return self
        field = self[0].account_id.currency_id and 'amount_residual_currency' or 'amount_residual'
        sm_debit_move, sm_credit_move = self._get_pair_to_reconcile()
        #there is no more pair to reconcile so return what move_line are left
        if not sm_credit_move or not sm_debit_move:
            return self

        #Reconcile the pair together
        amount_reconcile = min(sm_debit_move[field], -sm_credit_move[field])
        #Remove from recordset the one(s) that will be totally reconciled
        if amount_reconcile == sm_debit_move[field]:
            self -= sm_debit_move
        if amount_reconcile == -sm_credit_move[field]:
            self -= sm_credit_move

        #Check for the currency and amount_currency we can set
        currency = False
        amount_reconcile_currency = 0
        if sm_debit_move.currency_id == sm_credit_move.currency_id and sm_debit_move.currency_id.id:
            currency = sm_credit_move.currency_id.id
            amount_reconcile_currency = min(sm_debit_move.amount_residual_currency, -sm_credit_move.amount_residual_currency)

        amount_reconcile = min(sm_debit_move.amount_residual, -sm_credit_move.amount_residual)

        self.env['account.partial.reconcile'].create({
            'debit_move_id': sm_debit_move.id,
            'credit_move_id': sm_credit_move.id,
            'amount': amount_reconcile,
            'amount_currency': amount_reconcile_currency,
            'currency_id': currency,
        })

        #Iterate process again on self
        return self.auto_reconcile_lines()

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        #Perform all checks on lines
        company_ids = set()
        all_accounts = []
        partners = set()
        for line in self:
            company_ids.add(line.company_id.id)
            all_accounts.append(line.account_id)
            if (line.account_id.internal_type in ('receivable', 'payable')):
                partners.add(line.partner_id.id)
            if line.reconciled:
                raise UserError(_('You are trying to reconcile some entries that are already reconciled!'))
        if len(company_ids) > 1:
            raise UserError(_('To reconcile the entries company should be the same for all entries!'))
        if len(set(all_accounts)) > 1:
            raise UserError(_('Entries are not of the same account!'))
        if not all_accounts[0].reconcile:
            raise UserError(_('The account %s (%s) is not marked as reconciliable !') % (all_accounts[0].name, all_accounts[0].code))
        if len(partners) > 1:
            raise UserError(_('The partner has to be the same on all lines for receivable and payable accounts!'))

        #reconcile everything that can be
        remaining_moves = self.auto_reconcile_lines()

        #if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            writeoff_to_reconcile = remaining_moves._create_writeoff({'account_id': writeoff_acc_id.id, 'journal_id': writeoff_journal_id.id})
            #add writeoff line to reconcile algo and finish the reconciliation
            remaining_moves = (remaining_moves + writeoff_to_reconcile).auto_reconcile_lines()

    #TODO: need to be rewritten in a cleaner way
    def _create_writeoff(self, vals):
        """ Create a writeoff move for the account.move.lines in self. If debit/credit is not specified in vals,

            :param vals: dict containing values suitable fot account_move_line.create(). The data in vals will
                be processed to create bot writeoff acount.move.line and their enclosing account.move.
        """
        # Check and complete vals
        if 'account_id' not in vals or 'journal_id' not in vals:
            raise UserError("It is mandatory to specify an account and a journal to create a write-off.")
        if ('debit' in vals) ^ ('credit' in vals):
            raise UserError("Either pass both debit and credit or none.")
        company_currency = self[0].account_id.company_id.currency_id
        account_currency = self[0].account_id.currency_id or company_currency
        if 'credit' not in vals and 'debit' not in vals:
            amount = sum([r.amount_residual for r in self])
            vals['debit'] = amount > 0 and amount or 0.0
            vals['credit'] = amount < 0 and abs(amount) or 0.0
        if 'account_currency' not in vals and account_currency != company_currency:
            vals['currency_id'] = account_currency
            vals['amount_currency'] = sum([r.amount_residual_currency for r in self])
        if 'date' not in vals:
            vals['date'] = self._context.get('date_p') or time.strftime('%Y-%m-%d')
        if 'name' not in vals:
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
            rec_move_ids += account_move_line.matched_debit_ids
            rec_move_ids += account_move_line.matched_credit_ids
        return rec_move_ids.unlink()

    ####################################################
    # CRUD methods
    ####################################################

    @api.model
    def create(self, vals, apply_taxes=True):
        """ :param apply_taxes: set to False if you don't want vals['tax_ids'] to result in the creation of move lines for taxes and eventual
                adjustment of the line amount (in case of a tax included in price). This is useful for use cases where you don't want to
                apply taxes in the default fashion (eg. taxes). You can also pass 'dont_create_taxes' in context.

            :context's key `check_move_validity`: check data consistency after move line creation. Eg. set to false to disable verification that the move
                debit-credit == 0 while creating the move lines composing the move.

        """
        AccountObj = self.env['account.account']
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
            raise UserError(_('You cannot use deprecated account.'))
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
                    raise UserError(_('Cannot create an automatic sequence for this piece.\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.'))
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
            raise UserError(_('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

        # Create tax lines
        tax_lines_vals = []
        if apply_taxes and not context.get('dont_create_taxes') and vals.get('tax_ids'):
            # Get ids from triplets : https://www.odoo.com/documentation/master/reference/orm.html#openerp.models.Model.write
            tax_ids = map(lambda tax: tax[1], vals['tax_ids'])
            # Since create() receives ids instead of recordset, let's just use the old-api bridge
            res = self.env['account.tax']._model.compute_all(self._cr, self._uid, tax_ids, amount,
                vals.get('currency_id', None), 1, vals.get('product_id', None), vals.get('partner_id', None), context=context)
            # Adjust line amount if any tax is price_include
            if abs(res['total_excluded']) < abs(amount):
                if vals['debit'] != 0.0: vals['debit'] = res['total_excluded']
                if vals['credit'] != 0.0: vals['credit'] = -res['total_excluded']
                if vals.get('amount_currency'):
                    vals['amount_currency'] = self.env['res.currency'].browse(vals['currency_id']).round(vals['amount_currency'] * (amount / res['total_excluded']))
            # Create tax lines
            for tax_vals in res['taxes']:
                account_id = (amount > 0 and tax_vals['account_id'] or tax_vals['refund_account_id'])
                if not account_id: account_id = vals['account_id']
                tax_lines_vals.append({
                    'account_id': account_id,
                    'name': vals['name'] + ' ' + tax_vals['name'],
                    'tax_line_id': tax_vals['id'],
                    'move_id': vals['move_id'],
                    'date': vals['date'],
                    'partner_id': vals.get('partner_id'),
                    'ref': vals.get('ref'),
                    'statement_id': vals.get('statement_id'),
                    'debit': tax_vals['amount'] > 0 and tax_vals['amount'] or 0.0,
                    'credit': tax_vals['amount'] < 0 and -tax_vals['amount'] or 0.0,
                })

        new_line = super(AccountMoveLine, self).create(vals)
        for tax_line_vals in tax_lines_vals:
            # TODO: remove .with_context(context) once this context nonsense is solved
            self.with_context(context).create(tax_line_vals)

        if self._context.get('check_move_validity', True):
            move = MoveObj.browse(vals['move_id'])
            move.with_context(context)._post_validate()
            if journal.entry_posted:
                move.with_context(context).post()

        return new_line

    @api.multi
    def unlink(self):
        self._update_check()
        move_ids = set()
        for line in self:
            if line.move_id.id not in move_ids:
                move_ids.add(line.move_id.id)
        result = super(AccountMoveLine, self).unlink()
        if self._context.get('check_move_validity', True) and move_ids:
            self.env['account.move'].browse(list(move_ids))._post_validate()
        return result

    @api.multi
    def write(self, vals):
        if vals.get('tax_line_id') or vals.get('tax_ids'):
            raise UserError(_('You cannot change the tax, you should remove and recreate lines.'))
        if ('account_id' in vals) and self.env['account.account'].browse(vals['account_id']).deprecated:
            raise UserError(_('You cannot use deprecated account.'))
        if any(key in vals for key in ('account_id', 'journal_id', 'date', 'move_id', 'debit', 'credit', 'amount_currency', 'currency_id')):
            self._update_check()

        result = super(AccountMoveLine, self).write(vals)
        if self._context.get('check_move_validity', True):
            move_ids = set()
            for line in self:
                if line.move_id.id not in move_ids:
                    move_ids.add(line.move_id.id)
            self.env['account.move'].browse(list(move_ids))._post_validate()
        return result

    @api.multi
    def _update_check(self):
        """ Raise Warning to cause rollback if the move is posted, some entries are reconciled or the move is older than the lock date"""
        move_ids = set()
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft':
                raise UserError(_('You cannot do this modification on a posted journal entry, you can just change some non legal fields. You must revert the journal entry to cancel it.\n%s.') % err_msg)
            if line.reconciled:
                raise UserError(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            if line.move_id.id not in move_ids:
                move_ids.add(line.move_id.id)
            self.env['account.move'].browse(list(move_ids))._check_lock_date()
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
                    raise UserError(_("You have to define an analytic journal on the '%s' journal!") % (obj_line.journal_id.name, ))
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
            'amount': (obj_line.credit or 0.0) - (obj_line.debit or 0.0),
            'general_account_id': obj_line.account_id.id,
            'journal_id': obj_line.journal_id.analytic_journal_id.id,
            'ref': obj_line.ref,
            'move_id': obj_line.id,
            'user_id': self._uid,
        }

    @api.model
    def _query_get(self, domain=None):
        context = dict(self._context or {})
        domain = domain and safe_eval(domain) or []

        if context.get('date_to'):
            domain += [('date', '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', ('date', '>=', context['date_from']), ('account_id.user_type.include_initial_balance', '=', True)]
            else:
                domain += [('date', '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('move_id.state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]

        where_clause = ""
        where_clause_params = []
        if domain:
            query = self._where_calc(domain)
            dummy, where_clause, where_clause_params = query.get_sql()
        return where_clause, where_clause_params


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _description = "Partial Reconcile"

    debit_move_id = fields.Many2one('account.move.line')
    credit_move_id = fields.Many2one('account.move.line')
    amount = fields.Float()
    amount_currency = fields.Float(string="Amount in Currency")
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', related='debit_move_id.company_id', store=True, string='Currency')

    def create_exchange_rate_entry(self):
        """ Automatically create a journal entry to book the exchange rate difference between the `debit_move_id`
            and the `credit_move_id`, if both share the same currency, and at the prorata of the amount matched
            between them.
            That new journal entry is made in the company `currency_exchange_journal_id` and one of its journal
            items is matched with the other lines to ensure having the residual amount in company currency that
            reflects perfectly the residual amount in foreign currency.
        """
        for rec in self:
            if rec.currency_id and rec.debit_move_id.amount_currency and rec.credit_move_id.amount_currency:
                #create exchange rate difference journal entry
                rate_diff = rec.debit_move_id.debit / rec.debit_move_id.amount_currency - rec.credit_move_id.credit / -rec.credit_move_id.amount_currency
                if rec.amount_currency and rec.company_id.currency_id.round(rec.amount_currency * rate_diff):
                    if not rec.company_id.currency_exchange_journal_id:
                        raise UserError(_("You should configure the 'Exchange Rate Journal' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
                    if not self.company_id.income_currency_exchange_account_id.id:
                        raise UserError(_("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
                    if not self.company_id.expense_currency_exchange_account_id.id:
                        raise UserError(_("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
                    amount_diff = rec.company_id.currency_id.round(rec.amount_currency * rate_diff)
                    move = rec.env['account.move'].create({'journal_id': rec.company_id.currency_exchange_journal_id.id, 'rate_diff_partial_rec_id': rec.id})
                    line_to_reconcile = rec.env['account.move.line'].with_context(check_move_validity=False).create({
                        'name': _('Currency exchange rate difference'),
                        'debit': amount_diff < 0 and -amount_diff or 0.0,
                        'credit': amount_diff > 0 and amount_diff or 0.0,
                        'account_id': rec.debit_move_id.account_id.id,
                        'move_id': move.id,
                        'currency_id': rec.currency_id.id,
                    })
                    rec.env['account.move.line'].create({
                        'name': _('Currency exchange rate difference'),
                        'debit': amount_diff > 0 and amount_diff or 0.0,
                        'credit': amount_diff < 0 and -amount_diff or 0.0,
                        'account_id': amount_diff > 0 and rec.company_id.currency_exchange_journal_id.default_debit_account_id.id or rec.company_id.currency_exchange_journal_id.default_credit_account_id.id,
                        'move_id': move.id,
                        'currency_id': rec.currency_id.id,
                    })
                    rec.env['account.partial.reconcile'].create({
                        'debit_move_id': amount_diff < 0 and line_to_reconcile.id or rec.debit_move_id.id,
                        'credit_move_id': amount_diff > 0 and line_to_reconcile.id or rec.credit_move_id.id,
                        'amount': amount_diff,
                        'amount_currency': 0.0,
                        'currency_id': rec.debit_move_id.currency_id.id,
                    })

    @api.model
    def create(self, vals):
        res = super(AccountPartialReconcile, self).create(vals)
        #eventually create a journal entry to book the difference due to foreign currency's exchange rate that fluctuates
        res.create_exchange_rate_entry()
        return res

    @api.multi
    def unlink(self):
        """ When removing a link between entries, we need to revert the eventual journal entries we created to book the
            fluctuation of the foreign currency's exchange rate.
        """
        #TODO: do the below lines as soon os the reverse entry feature/wizard is implemented
        exchange_rate_entries = self.env['account.move'].search([('rate_diff_partial_rec_id', 'in', self.ids)])
        exchange_rate_entries.reverse_moves()
        return super(AccountPartialReconcile, self).unlink()
