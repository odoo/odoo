# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _order = "first_line_index desc"
    _check_company_auto = True

    @api.model
    def default_get(self, fields_list):
        # EXTENDS base
        defaults = super().default_get(fields_list)
        # create statement on a saved statement line in the tree view
        if self._context.get('st_line_id'):
            st_line = self.env['account.bank.statement.line'].browse(self._context['st_line_id'])
            defaults['balance_start'] = st_line.running_balance - st_line.amount
            return defaults
        # create statement from a new line in the tree view, not stored in the db yet
        if self._context.get('st_line_date'):
            defaults['balance_start'] = self.env['account.bank.statement.line'].search(
                domain=[
                    ('date', '<=', self._context['st_line_date']),
                    ('journal_id', '=', self._context.get('st_line_journal_id')),
                ],
                order='internal_index desc',
                limit=1
            ).running_balance
            return defaults
        lines = None
        # creating statements with split button
        if self._context.get('split_line_id'):
            current_st_line = self.env['account.bank.statement.line'].browse(self.env.context.get('split_line_id'))
            line_before = self.env['account.bank.statement.line'].search(
                domain=[
                    ('internal_index', '<', current_st_line.internal_index),
                    ('journal_id', '=', current_st_line.journal_id.id),
                    ('statement_id', '!=', current_st_line.statement_id.id),
                    ('statement_id', '!=', False),
                ],
                order='internal_index desc',
                limit=1,
            )
            lines = self.env['account.bank.statement.line'].search(
                domain=[
                    ('internal_index', '<=', current_st_line.internal_index),
                    ('internal_index', '>', line_before.internal_index or ''),
                    ('journal_id', '=', current_st_line.journal_id.id),
                ],
                order='internal_index desc',
            )
        # if it is called from the action menu, we can have both start and end balances and we filter out
        # completed statements, because it is probably due to a mistake from the user
        elif self._context.get('active_model') == 'account.bank.statement.line' and self._context.get('active_ids'):
            lines = self.env['account.bank.statement.line'].browse(self._context.get('active_ids')) \
                .filtered(lambda line: not line.statement_complete) \
                .sorted()
            if not lines:
                raise UserError(_('One or more selected lines already belong to a complete statement.'))
        if lines:
            defaults['line_ids'] = [Command.set(lines.ids)]
            defaults['balance_start'] = lines[-1:].running_balance - lines[-1:].amount
            defaults['balance_end_real'] = lines[:1].running_balance

        return defaults

    name = fields.Char(
        string='Reference',
        copy=False,
    )

    # Used to hold the reference of the external mean that created this statement (name of imported file,
    # reference of online synchronization...)
    reference = fields.Char(
        string='External Reference',
        copy=False,
    )

    date = fields.Date(
        compute='_compute_date_index', store=True,
    )

    # The internal index of the first line of a statement, it is used for sorting the statements
    # The date field cannot be used as there might be more than one statement in one day.
    # keeping this order is important because the validity of the statements are based on their order
    first_line_index = fields.Char(
        comodel_name='account.bank.statement.line',
        compute='_compute_date_index', store=True, index=True,
    )

    balance_start = fields.Monetary(
        string='Starting Balance',
        default=0.0,
    )

    # Balance end is calculated based on the statement line amounts and real starting balance.
    balance_end = fields.Monetary(
        string='Computed Balance',
        compute='_compute_balance_end', store=True,
    )

    balance_end_real = fields.Monetary(
        string='Ending Balance',
        default=0.0,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        related='journal_id.company_id', store=True,
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
    )

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True,
        check_company=True,
    )

    line_ids = fields.One2many(
        comodel_name='account.bank.statement.line',
        inverse_name='statement_id',
        string='Statement lines',
        required=True,
    )

    # A statement assumed to be complete when the sum of encoded lines is equal to the difference between initial and
    # ending balances. In other words, a statement is complete when there are enough lines to fill the value between
    # initial and final balances. When the user reaches this point, the statement is not autofilled on the new lines.
    is_complete = fields.Boolean(
        compute='_compute_is_complete', store=True,
    )

    # A statement is considered valid when the starting balance matches the ending balance of the previous statement.
    # The lines without statements are neglected because, either the user is using statements regularly, so they can
    # assume every line without statement is problematic, or they don't use them regularly, in that case statements are
    # working as checkpoints only and their validity is not important.
    # The first statement of a journal is always considered valid. The validity of the statement is based on other
    # statements, so one can say this is external integrity check were as is_complete is the internal integrity.
    is_valid = fields.Boolean(
        compute='_compute_is_valid',
        search='_search_is_valid',
    )

    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('line_ids.internal_index')
    def _compute_date_index(self):
        for stmt in self:
            sorted_lines = stmt.line_ids.sorted('internal_index')
            stmt.date = sorted_lines[-1:].date
            stmt.first_line_index = sorted_lines[:1].internal_index

    @api.depends('balance_start', 'line_ids.amount')
    def _compute_balance_end(self):
        for statement in self:
            statement.balance_end = statement.balance_start + sum(statement.line_ids.mapped('amount'))

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for statement in self:
            statement.currency_id = statement.journal_id.currency_id or statement.company_id.currency_id

    @api.depends('line_ids.journal_id')
    def _compute_journal_id(self):
        for statement in self:
            statement.journal_id = statement.line_ids.journal_id

    @api.depends('balance_end_real', 'balance_end')
    def _compute_is_complete(self):
        for stmt in self:
            stmt.is_complete = stmt.line_ids and stmt.currency_id.compare_amounts(
                stmt.balance_end, stmt.balance_end_real) == 0

    def _compute_is_valid(self):
        # we extract the invalid statements, the statements with no lines and the first statement are not in the query
        # because they don't have a previous statement, so they are excluded from the join, and we consider them valid.
        # if we have extracted the valid ones, we would have to mark above-mentioned statements valid manually
        invalids = self.filtered(lambda s: s.id in self._get_invalid_statement_ids())
        invalids.is_valid = False
        (self - invalids).is_valid = True

    def _search_is_valid(self, operator, value):
        if operator not in ('=', '!=', '<>'):
            raise UserError(_('Operation not supported'))
        invalid_ids = self._get_invalid_statement_ids(all_statements=True)
        if operator in ('!=', '<>') and value or operator == '=' and not value:
            return [('id', 'in', invalid_ids)]
        return [('id', 'not in', invalid_ids)]

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
<<<<<<< HEAD
        # EXTENDS base
        # If we are doing a split, we have to correct the split statement's balance to keep both original and new
        # statements complete and valid.
        if self._context.get('split_line_id'):
            old_statement = self.env['account.bank.statement.line'].browse(self._context.get('split_line_id')).statement_id
            old_lines = old_statement.line_ids
        statements = super().create(vals_list)
        if self._context.get('split_line_id'):
            statements.ensure_one()
            if old_statement:
                net_change = sum((statements.line_ids & old_lines).mapped('amount'))
                old_statement.balance_start += net_change
        return statements
||||||| parent of 31c873ac85ca... temp
        # OVERRIDE
        counterpart_account_ids = []

        for vals in vals_list:
            statement = self.env['account.bank.statement'].browse(vals['statement_id'])
            if statement.state != 'open' and self._context.get('check_move_validity', True):
                raise UserError(_("You can only create statement line in open bank statements."))

            # Force the move_type to avoid inconsistency with residual 'default_move_type' inside the context.
            vals['move_type'] = 'entry'

            journal = statement.journal_id
            # Ensure the journal is the same as the statement one.
            vals['journal_id'] = journal.id
            vals['currency_id'] = (journal.currency_id or journal.company_id.currency_id).id
            if 'date' not in vals:
                vals['date'] = statement.date

            # Hack to force different account instead of the suspense account.
            counterpart_account_ids.append(vals.pop('counterpart_account_id', None))

        st_lines = super().create(vals_list)

        for i, st_line in enumerate(st_lines):
            counterpart_account_id = counterpart_account_ids[i]

            to_write = {'statement_line_id': st_line.id, 'narration': st_line.narration}
            if 'line_ids' not in vals_list[i]:
                to_write['line_ids'] = [(0, 0, line_vals) for line_vals in st_line._prepare_move_line_default_vals(counterpart_account_id=counterpart_account_id)]

            st_line.move_id.write(to_write)

            # Otherwise field narration will be recomputed silently (at next flush) when writing on partner_id
            self.env.remove_to_compute(st_line.move_id._fields['narration'], st_line.move_id)
        return st_lines

    def write(self, vals):
        # OVERRIDE
        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    def unlink(self):
        # OVERRIDE to unlink the inherited account.move (move_id field) as well.
        moves = self.with_context(force_delete=True).mapped('move_id')
        res = super().unlink()
        moves.unlink()
        return res

    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.bank.statement.line <-> account.move
    # -------------------------------------------------------------------------

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.bank.statement.line regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            move = st_line.move_id
            move_vals_to_write = {}
            st_line_vals_to_write = {}

            if 'state' in changed_fields:
                if (st_line.state == 'open' and move.state != 'draft') or (st_line.state in ('posted', 'confirm') and move.state != 'posted'):
                    raise UserError(_(
                        "You can't manually change the state of journal entry %s, as it has been created by bank "
                        "statement %s."
                    ) % (st_line.move_id.display_name, st_line.statement_id.display_name))

            if 'line_ids' in changed_fields:
                liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
                company_currency = st_line.journal_id.company_id.currency_id
                journal_currency = st_line.journal_id.currency_id if st_line.journal_id.currency_id != company_currency else False

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state regarding its related statement line.\n"
                        "To be consistent, the journal entry must always have exactly one journal item involving the "
                        "bank/cash account."
                    ) % st_line.move_id.display_name)

                st_line_vals_to_write.update({
                    'payment_ref': liquidity_lines.name,
                    'partner_id': liquidity_lines.partner_id.id,
                })

                # Update 'amount' according to the liquidity line.

                if journal_currency:
                    st_line_vals_to_write.update({
                        'amount': liquidity_lines.amount_currency,
                    })
                else:
                    st_line_vals_to_write.update({
                        'amount': liquidity_lines.balance,
                    })

                if len(suspense_lines) == 1:

                    if journal_currency and suspense_lines.currency_id == journal_currency:

                        # The suspense line is expressed in the journal's currency meaning the foreign currency
                        # set on the statement line is no longer needed.

                        st_line_vals_to_write.update({
                            'amount_currency': 0.0,
                            'foreign_currency_id': False,
                        })

                    elif not journal_currency and suspense_lines.currency_id == company_currency:

                        # Don't set a specific foreign currency on the statement line.

                        st_line_vals_to_write.update({
                            'amount_currency': 0.0,
                            'foreign_currency_id': False,
                        })

                    else:

                        # Update the statement line regarding the foreign currency of the suspense line.

                        st_line_vals_to_write.update({
                            'amount_currency': -suspense_lines.amount_currency,
                            'foreign_currency_id': suspense_lines.currency_id.id,
                        })

                move_vals_to_write.update({
                    'partner_id': liquidity_lines.partner_id.id,
                    'currency_id': (st_line.foreign_currency_id or journal_currency or company_currency).id,
                })

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            st_line.write(move._cleanup_write_orm_values(st_line, st_line_vals_to_write))

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.bank.statement.line.
        :param changed_fields: A list containing all modified fields on account.bank.statement.line.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
            'payment_ref', 'amount', 'amount_currency',
            'foreign_currency_id', 'currency_id', 'partner_id',
        )):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
            company_currency = st_line.journal_id.company_id.currency_id
            journal_currency = st_line.journal_id.currency_id if st_line.journal_id.currency_id != company_currency else False

            line_vals_list = st_line._prepare_move_line_default_vals()
            line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]

            if suspense_lines:
                line_ids_commands.append((1, suspense_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in other_lines:
                line_ids_commands.append((2, line.id))

            st_line_vals = {
                'currency_id': (st_line.foreign_currency_id or journal_currency or company_currency).id,
                'line_ids': line_ids_commands,
            }
            if st_line.move_id.partner_id != st_line.partner_id:
                st_line_vals['partner_id'] = st_line.partner_id.id
            st_line.move_id.write(st_line_vals)

    # -------------------------------------------------------------------------
    # RECONCILIATION METHODS
    # -------------------------------------------------------------------------

    def _prepare_reconciliation(self, lines_vals_list, allow_partial=False):
        ''' Helper for the "reconcile" method used to get a full preview of the reconciliation result. This method is
        quite useful to deal with reconcile models or the reconciliation widget because it ensures the values seen by
        the user are exactly the values you get after reconciling.

        :param lines_vals_list: See the 'reconcile' method.
        :param allow_partial:   In case of matching a line having an higher amount, allow creating a partial instead
                                an open balance on the statement line.
        :return: The diff to be applied on the statement line as a tuple
        (
            lines_to_create:    The values to create the account.move.line on the statement line.
            payments_to_create: The values to create the account.payments.
            open_balance_vals:  A dictionary to create the open-balance line or None if the reconciliation is full.
            existing_lines:     The counterpart lines to which the reconciliation will be done.
        )
        '''
        self.ensure_one()
        journal = self.journal_id
        company_currency = journal.company_id.currency_id
        foreign_currency = self.foreign_currency_id or journal.currency_id or company_currency

        liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()

        # Ensure the statement line has not yet been already reconciled.
        # If the move has 'to_check' enabled, it means the statement line has created some lines that
        # need to be checked later and replaced by the real ones.
        if not self.move_id.to_check and other_lines:
            raise UserError(_("The statement line has already been reconciled."))

        # A list of dictionary containing:
        # - line_vals:          The values to create the account.move.line on the statement line.
        # - payment_vals:       The optional values to create a bridge account.payment
        # - counterpart_line:   The optional counterpart line to reconcile with 'line'.
        reconciliation_overview = []

        total_balance = liquidity_lines.balance
        total_amount_currency = liquidity_lines.amount_currency
        sign = 1 if liquidity_lines.balance > 0.0 else -1

        # Step 1: Split 'lines_vals_list' into two batches:
        # - The existing account.move.lines that need to be reconciled with the statement line.
        #       => Will be managed at step 2.
        # - The account.move.lines to be created from scratch.
        #       => Will be managed directly.

        # In case of the payment is matched directly with an higher amount, don't create an open
        # balance but a partial reconciliation.
        partial_rec_needed = allow_partial

        to_browse_ids = []
        to_process_vals = []
        for vals in lines_vals_list:
            # Don't modify the params directly.
            vals = dict(vals)

            if 'id' in vals:
                # Existing account.move.line.
                to_browse_ids.append(vals.pop('id'))
                to_process_vals.append(vals)
                if any(x in vals for x in ('balance', 'amount_residual', 'amount_residual_currency')):
                    partial_rec_needed = False
            else:
                # Newly created account.move.line from scratch.
                line_vals = self._prepare_counterpart_move_line_vals(vals)
                total_balance += line_vals['debit'] - line_vals['credit']
                total_amount_currency += line_vals['amount_currency']
                reconciliation_overview.append({'line_vals': line_vals})
                partial_rec_needed = False

        # Step 2: Browse counterpart lines all in one and process them.

        existing_lines = self.env['account.move.line'].browse(to_browse_ids)

        i = 0
        for line, counterpart_vals in zip(existing_lines, to_process_vals):
            line_vals = self._prepare_counterpart_move_line_vals(counterpart_vals, move_line=line)
            balance = line_vals['debit'] - line_vals['credit']
            amount_currency = line_vals['amount_currency']
            i += 1

            if i == len(existing_lines):
                # Last line.

                if partial_rec_needed and sign * (total_amount_currency + amount_currency) < 0.0:

                    # On the last aml, when the total matched amount becomes higher than the residual amount of the
                    # statement line, make sure to not create an open balance later.
                    line_vals = self._prepare_counterpart_move_line_vals(
                        {
                            **counterpart_vals,
                            'amount_residual': -math.copysign(total_balance, balance),
                            'amount_residual_currency': -math.copysign(total_amount_currency, amount_currency),
                            'currency_id': foreign_currency.id,
                        },
                        move_line=line,
                    )
                    balance = line_vals['debit'] - line_vals['credit']
                    amount_currency = line_vals['amount_currency']

            elif sign * total_amount_currency < 0.0:
                # The partial reconciliation is no longer an option since the total matched amount is now higher than
                # the residual amount of the statement line but this is not the last line to process. Then, since we
                # don't want to create zero balance lines, do nothing and let the open-balance be created like it
                # should.
                partial_rec_needed = False

            total_balance += balance
            total_amount_currency += amount_currency

            reconciliation_overview.append({
                'line_vals': line_vals,
                'counterpart_line': line,
            })

        # Step 3: Fix rounding issue due to currency conversions.
        # Add the remaining balance on the first encountered line starting with the custom ones.

        if foreign_currency.is_zero(total_amount_currency) and not company_currency.is_zero(total_balance):
            vals = reconciliation_overview[0]['line_vals']
            new_balance = vals['debit'] - vals['credit'] - total_balance
            vals.update({
                'debit': new_balance if new_balance > 0.0 else 0.0,
                'credit': -new_balance if new_balance < 0.0 else 0.0,
            })
            total_balance = 0.0

        # Step 4: If the journal entry is not yet balanced, create an open balance.

        if self.company_currency_id.round(total_balance):
            counterpart_vals = {
                'name': '%s: %s' % (self.payment_ref, _('Open Balance')),
                'balance': -total_balance,
                'currency_id': self.company_currency_id.id,
            }

            partner = self.partner_id or existing_lines.mapped('partner_id')[:1]
            if partner:
                if self.amount > 0:
                    open_balance_account = partner.with_company(self.company_id).property_account_receivable_id
                else:
                    open_balance_account = partner.with_company(self.company_id).property_account_payable_id

                counterpart_vals['account_id'] = open_balance_account.id
                counterpart_vals['partner_id'] = partner.id
            else:
                if self.amount > 0:
                    open_balance_account = self.company_id.partner_id.with_company(self.company_id).property_account_receivable_id
                else:
                    open_balance_account = self.company_id.partner_id.with_company(self.company_id).property_account_payable_id
                counterpart_vals['account_id'] = open_balance_account.id

            open_balance_vals = self._prepare_counterpart_move_line_vals(counterpart_vals)
        else:
            open_balance_vals = None

        return reconciliation_overview, open_balance_vals

    def reconcile(self, lines_vals_list, to_check=False, allow_partial=False):
        ''' Perform a reconciliation on the current account.bank.statement.line with some
        counterpart account.move.line.
        If the statement line entry is not fully balanced after the reconciliation, an open balance will be created
        using the partner.

        :param lines_vals_list: A list of python dictionary containing:
            'id':               Optional id of an existing account.move.line.
                                For each line having an 'id', a new line will be created in the current statement line.
            'balance':          Optional amount to consider during the reconciliation. If a foreign currency is set on the
                                counterpart line in the same foreign currency as the statement line, then this amount is
                                considered as the amount in foreign currency. If not specified, the full balance is taken.
                                This value must be provided if 'id' is not.
            **kwargs:           Custom values to be set on the newly created account.move.line.
        :param to_check:        Mark the current statement line as "to_check" (see field for more details).
        :param allow_partial:   In case of matching a line having an higher amount, allow creating a partial instead
                                of an open balance on the statement line.
        '''
        self.ensure_one()
        liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()

        reconciliation_overview, open_balance_vals = self._prepare_reconciliation(
            lines_vals_list,
            allow_partial=allow_partial,
        )

        # ==== Manage res.partner.bank ====

        if self.account_number and self.partner_id and not self.partner_bank_id:
            self.partner_bank_id = self._find_or_create_bank_account()

        # ==== Check open balance ====

        if open_balance_vals:
            if not open_balance_vals.get('partner_id'):
                raise UserError(_("Unable to create an open balance for a statement line without a partner set."))
            if not open_balance_vals.get('account_id'):
                raise UserError(_("Unable to create an open balance for a statement line because the receivable "
                                  "/ payable accounts are missing on the partner."))

        # ==== Create & reconcile lines on the bank statement line ====

        to_create_commands = [(0, 0, open_balance_vals)] if open_balance_vals else []
        to_delete_commands = [(2, line.id) for line in suspense_lines + other_lines]

        # Cleanup previous lines.
        self.move_id.with_context(check_move_validity=False, skip_account_move_synchronization=True, force_delete=True).write({
            'line_ids': to_delete_commands + to_create_commands,
            'to_check': to_check,
        })

        line_vals_list = [reconciliation_vals['line_vals'] for reconciliation_vals in reconciliation_overview]
        new_lines = self.env['account.move.line'].create(line_vals_list)
        new_lines = new_lines.with_context(skip_account_move_synchronization=True)
        for reconciliation_vals, line in zip(reconciliation_overview, new_lines):
            if reconciliation_vals.get('counterpart_line'):
                counterpart_line = reconciliation_vals['counterpart_line']
            else:
                continue

            (line + counterpart_line).reconcile()

        # Assign partner if needed (for example, when reconciling a statement
        # line with no partner, with an invoice; assign the partner of this invoice)
        if not self.partner_id:
            rec_overview_partners = set(overview['counterpart_line'].partner_id.id
                                        for overview in reconciliation_overview
                                        if overview.get('counterpart_line'))
            if len(rec_overview_partners) == 1 and rec_overview_partners != {False}:
                self.line_ids.write({'partner_id': rec_overview_partners.pop()})

        # Refresh analytic lines.
        self.move_id.line_ids.analytic_line_ids.unlink()
        self.move_id.line_ids.create_analytic_lines()
=======
        # OVERRIDE
        counterpart_account_ids = []

        for vals in vals_list:
            statement = self.env['account.bank.statement'].browse(vals['statement_id'])
            if statement.state != 'open' and self._context.get('check_move_validity', True):
                raise UserError(_("You can only create statement line in open bank statements."))

            # Force the move_type to avoid inconsistency with residual 'default_move_type' inside the context.
            vals['move_type'] = 'entry'

            journal = statement.journal_id
            # Ensure the journal is the same as the statement one.
            vals['journal_id'] = journal.id
            vals['currency_id'] = (journal.currency_id or journal.company_id.currency_id).id
            if 'date' not in vals:
                vals['date'] = statement.date

            # Hack to force different account instead of the suspense account.
            counterpart_account_ids.append(vals.pop('counterpart_account_id', None))

        st_lines = super().create(vals_list)

        for i, st_line in enumerate(st_lines):
            counterpart_account_id = counterpart_account_ids[i]

            to_write = {'statement_line_id': st_line.id, 'narration': st_line.narration}
            if 'line_ids' not in vals_list[i]:
                to_write['line_ids'] = [(0, 0, line_vals) for line_vals in st_line._prepare_move_line_default_vals(counterpart_account_id=counterpart_account_id)]

            st_line.move_id.write(to_write)

            # Otherwise field narration will be recomputed silently (at next flush) when writing on partner_id
            self.env.remove_to_compute(st_line.move_id._fields['narration'], st_line.move_id)
        return st_lines

    def write(self, vals):
        # OVERRIDE
        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    def unlink(self):
        # OVERRIDE to unlink the inherited account.move (move_id field) as well.
        moves = self.with_context(force_delete=True).mapped('move_id')
        res = super().unlink()
        moves.unlink()
        return res

    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.bank.statement.line <-> account.move
    # -------------------------------------------------------------------------

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.bank.statement.line regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            move = st_line.move_id
            move_vals_to_write = {}
            st_line_vals_to_write = {}

            if 'state' in changed_fields:
                if (st_line.state == 'open' and move.state != 'draft') or (st_line.state in ('posted', 'confirm') and move.state != 'posted'):
                    raise UserError(_(
                        "You can't manually change the state of journal entry %s, as it has been created by bank "
                        "statement %s."
                    ) % (st_line.move_id.display_name, st_line.statement_id.display_name))

            if 'line_ids' in changed_fields:
                liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
                company_currency = st_line.journal_id.company_id.currency_id
                journal_currency = st_line.journal_id.currency_id if st_line.journal_id.currency_id != company_currency else False

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state regarding its related statement line.\n"
                        "To be consistent, the journal entry must always have exactly one journal item involving the "
                        "bank/cash account."
                    ) % st_line.move_id.display_name)

                st_line_vals_to_write.update({
                    'payment_ref': liquidity_lines.name,
                    'partner_id': liquidity_lines.partner_id.id,
                })

                # Update 'amount' according to the liquidity line.

                if journal_currency:
                    st_line_vals_to_write.update({
                        'amount': liquidity_lines.amount_currency,
                    })
                else:
                    st_line_vals_to_write.update({
                        'amount': liquidity_lines.balance,
                    })

                if len(suspense_lines) == 1:

                    if journal_currency and suspense_lines.currency_id == journal_currency:

                        # The suspense line is expressed in the journal's currency meaning the foreign currency
                        # set on the statement line is no longer needed.

                        st_line_vals_to_write.update({
                            'amount_currency': 0.0,
                            'foreign_currency_id': False,
                        })

                    elif not journal_currency and suspense_lines.currency_id == company_currency:

                        # Don't set a specific foreign currency on the statement line.

                        st_line_vals_to_write.update({
                            'amount_currency': 0.0,
                            'foreign_currency_id': False,
                        })

                    else:

                        # Update the statement line regarding the foreign currency of the suspense line.

                        st_line_vals_to_write.update({
                            'amount_currency': -suspense_lines.amount_currency,
                            'foreign_currency_id': suspense_lines.currency_id.id,
                        })

                move_vals_to_write.update({
                    'partner_id': liquidity_lines.partner_id.id,
                    'currency_id': (st_line.foreign_currency_id or journal_currency or company_currency).id,
                })

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            st_line.write(move._cleanup_write_orm_values(st_line, st_line_vals_to_write))

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.bank.statement.line.
        :param changed_fields: A list containing all modified fields on account.bank.statement.line.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
            'payment_ref', 'amount', 'amount_currency',
            'foreign_currency_id', 'currency_id', 'partner_id',
        )):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
            company_currency = st_line.journal_id.company_id.currency_id
            journal_currency = st_line.journal_id.currency_id if st_line.journal_id.currency_id != company_currency else False

            line_vals_list = st_line._prepare_move_line_default_vals()
            line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]

            if suspense_lines:
                line_ids_commands.append((1, suspense_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in other_lines:
                line_ids_commands.append((2, line.id))

            st_line_vals = {
                'currency_id': (st_line.foreign_currency_id or journal_currency or company_currency).id,
                'line_ids': line_ids_commands,
            }
            if st_line.move_id.partner_id != st_line.partner_id:
                st_line_vals['partner_id'] = st_line.partner_id.id
            st_line.move_id.write(st_line_vals)

    # -------------------------------------------------------------------------
    # RECONCILIATION METHODS
    # -------------------------------------------------------------------------

    def _prepare_reconciliation(self, lines_vals_list, allow_partial=False):
        ''' Helper for the "reconcile" method used to get a full preview of the reconciliation result. This method is
        quite useful to deal with reconcile models or the reconciliation widget because it ensures the values seen by
        the user are exactly the values you get after reconciling.

        :param lines_vals_list: See the 'reconcile' method.
        :param allow_partial:   In case of matching a line having an higher amount, allow creating a partial instead
                                an open balance on the statement line.
        :return: The diff to be applied on the statement line as a tuple
        (
            lines_to_create:    The values to create the account.move.line on the statement line.
            payments_to_create: The values to create the account.payments.
            open_balance_vals:  A dictionary to create the open-balance line or None if the reconciliation is full.
            existing_lines:     The counterpart lines to which the reconciliation will be done.
        )
        '''
        self.ensure_one()
        journal = self.journal_id
        company_currency = journal.company_id.currency_id
        foreign_currency = self.foreign_currency_id or journal.currency_id or company_currency

        liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()

        # Ensure the statement line has not yet been already reconciled.
        # If the move has 'to_check' enabled, it means the statement line has created some lines that
        # need to be checked later and replaced by the real ones.
        if not self.move_id.to_check and other_lines:
            raise UserError(_("The statement line has already been reconciled."))

        # A list of dictionary containing:
        # - line_vals:          The values to create the account.move.line on the statement line.
        # - payment_vals:       The optional values to create a bridge account.payment
        # - counterpart_line:   The optional counterpart line to reconcile with 'line'.
        reconciliation_overview = []

        total_balance = liquidity_lines.balance
        total_amount_currency = -self._prepare_move_line_default_vals()[1]['amount_currency']
        sign = 1 if liquidity_lines.balance > 0.0 else -1

        # Step 1: Split 'lines_vals_list' into two batches:
        # - The existing account.move.lines that need to be reconciled with the statement line.
        #       => Will be managed at step 2.
        # - The account.move.lines to be created from scratch.
        #       => Will be managed directly.

        # In case of the payment is matched directly with an higher amount, don't create an open
        # balance but a partial reconciliation.
        partial_rec_needed = allow_partial

        to_browse_ids = []
        to_process_vals = []
        for vals in lines_vals_list:
            # Don't modify the params directly.
            vals = dict(vals)

            if 'id' in vals:
                # Existing account.move.line.
                to_browse_ids.append(vals.pop('id'))
                to_process_vals.append(vals)
                if any(x in vals for x in ('balance', 'amount_residual', 'amount_residual_currency')):
                    partial_rec_needed = False
            else:
                # Newly created account.move.line from scratch.
                line_vals = self._prepare_counterpart_move_line_vals(vals)
                total_balance += line_vals['debit'] - line_vals['credit']
                total_amount_currency += line_vals['amount_currency']
                reconciliation_overview.append({'line_vals': line_vals})
                partial_rec_needed = False

        # Step 2: Browse counterpart lines all in one and process them.

        existing_lines = self.env['account.move.line'].browse(to_browse_ids)

        i = 0
        for line, counterpart_vals in zip(existing_lines, to_process_vals):
            line_vals = self._prepare_counterpart_move_line_vals(counterpart_vals, move_line=line)
            balance = line_vals['debit'] - line_vals['credit']
            amount_currency = line_vals['amount_currency']
            i += 1

            if i == len(existing_lines):
                # Last line.

                if partial_rec_needed and sign * (total_amount_currency + amount_currency) < 0.0:

                    # On the last aml, when the total matched amount becomes higher than the residual amount of the
                    # statement line, make sure to not create an open balance later.
                    line_vals = self._prepare_counterpart_move_line_vals(
                        {
                            **counterpart_vals,
                            'amount_residual': -math.copysign(total_balance, balance),
                            'amount_residual_currency': -math.copysign(total_amount_currency, amount_currency),
                            'currency_id': foreign_currency.id,
                        },
                        move_line=line,
                    )
                    balance = line_vals['debit'] - line_vals['credit']
                    amount_currency = line_vals['amount_currency']

            elif sign * total_amount_currency < 0.0:
                # The partial reconciliation is no longer an option since the total matched amount is now higher than
                # the residual amount of the statement line but this is not the last line to process. Then, since we
                # don't want to create zero balance lines, do nothing and let the open-balance be created like it
                # should.
                partial_rec_needed = False

            total_balance += balance
            total_amount_currency += amount_currency

            reconciliation_overview.append({
                'line_vals': line_vals,
                'counterpart_line': line,
            })

        # Step 3: Fix rounding issue due to currency conversions.
        # Add the remaining balance on the first encountered line starting with the custom ones.

        if foreign_currency.is_zero(total_amount_currency) and not company_currency.is_zero(total_balance):
            vals = reconciliation_overview[0]['line_vals']
            new_balance = vals['debit'] - vals['credit'] - total_balance
            vals.update({
                'debit': new_balance if new_balance > 0.0 else 0.0,
                'credit': -new_balance if new_balance < 0.0 else 0.0,
            })
            total_balance = 0.0

        # Step 4: If the journal entry is not yet balanced, create an open balance.

        if self.company_currency_id.round(total_balance):
            counterpart_vals = {
                'name': '%s: %s' % (self.payment_ref, _('Open Balance')),
                'balance': -total_balance,
                'currency_id': self.company_currency_id.id,
            }

            partner = self.partner_id or existing_lines.mapped('partner_id')[:1]
            if partner:
                if self.amount > 0:
                    open_balance_account = partner.with_company(self.company_id).property_account_receivable_id
                else:
                    open_balance_account = partner.with_company(self.company_id).property_account_payable_id

                counterpart_vals['account_id'] = open_balance_account.id
                counterpart_vals['partner_id'] = partner.id
            else:
                if self.amount > 0:
                    open_balance_account = self.company_id.partner_id.with_company(self.company_id).property_account_receivable_id
                else:
                    open_balance_account = self.company_id.partner_id.with_company(self.company_id).property_account_payable_id
                counterpart_vals['account_id'] = open_balance_account.id

            open_balance_vals = self._prepare_counterpart_move_line_vals(counterpart_vals)
        else:
            open_balance_vals = None

        return reconciliation_overview, open_balance_vals

    def reconcile(self, lines_vals_list, to_check=False, allow_partial=False):
        ''' Perform a reconciliation on the current account.bank.statement.line with some
        counterpart account.move.line.
        If the statement line entry is not fully balanced after the reconciliation, an open balance will be created
        using the partner.

        :param lines_vals_list: A list of python dictionary containing:
            'id':               Optional id of an existing account.move.line.
                                For each line having an 'id', a new line will be created in the current statement line.
            'balance':          Optional amount to consider during the reconciliation. If a foreign currency is set on the
                                counterpart line in the same foreign currency as the statement line, then this amount is
                                considered as the amount in foreign currency. If not specified, the full balance is taken.
                                This value must be provided if 'id' is not.
            **kwargs:           Custom values to be set on the newly created account.move.line.
        :param to_check:        Mark the current statement line as "to_check" (see field for more details).
        :param allow_partial:   In case of matching a line having an higher amount, allow creating a partial instead
                                of an open balance on the statement line.
        '''
        self.ensure_one()
        liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()

        reconciliation_overview, open_balance_vals = self._prepare_reconciliation(
            lines_vals_list,
            allow_partial=allow_partial,
        )

        # ==== Manage res.partner.bank ====

        if self.account_number and self.partner_id and not self.partner_bank_id:
            self.partner_bank_id = self._find_or_create_bank_account()

        # ==== Check open balance ====

        if open_balance_vals:
            if not open_balance_vals.get('partner_id'):
                raise UserError(_("Unable to create an open balance for a statement line without a partner set."))
            if not open_balance_vals.get('account_id'):
                raise UserError(_("Unable to create an open balance for a statement line because the receivable "
                                  "/ payable accounts are missing on the partner."))

        # ==== Create & reconcile lines on the bank statement line ====

        to_create_commands = [(0, 0, open_balance_vals)] if open_balance_vals else []
        to_delete_commands = [(2, line.id) for line in suspense_lines + other_lines]

        # Cleanup previous lines.
        self.move_id.with_context(check_move_validity=False, skip_account_move_synchronization=True, force_delete=True).write({
            'line_ids': to_delete_commands + to_create_commands,
            'to_check': to_check,
        })

        line_vals_list = [reconciliation_vals['line_vals'] for reconciliation_vals in reconciliation_overview]
        new_lines = self.env['account.move.line'].create(line_vals_list)
        new_lines = new_lines.with_context(skip_account_move_synchronization=True)
        for reconciliation_vals, line in zip(reconciliation_overview, new_lines):
            if reconciliation_vals.get('counterpart_line'):
                counterpart_line = reconciliation_vals['counterpart_line']
            else:
                continue

            (line + counterpart_line).reconcile()

        # Assign partner if needed (for example, when reconciling a statement
        # line with no partner, with an invoice; assign the partner of this invoice)
        if not self.partner_id:
            rec_overview_partners = set(overview['counterpart_line'].partner_id.id
                                        for overview in reconciliation_overview
                                        if overview.get('counterpart_line'))
            if len(rec_overview_partners) == 1 and rec_overview_partners != {False}:
                self.line_ids.write({'partner_id': rec_overview_partners.pop()})

        # Refresh analytic lines.
        self.move_id.line_ids.analytic_line_ids.unlink()
        self.move_id.line_ids.create_analytic_lines()
>>>>>>> 31c873ac85ca... temp

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def _get_invalid_statement_ids(self, all_statements=None):
        """ Returns the statements that are invalid for _compute and _search methods."""

        self.env['account.bank.statement.line'].flush_model(['statement_id', 'internal_index'])
        self.env['account.bank.statement'].flush_model(['balance_start', 'balance_end_real', 'first_line_index'])

        self.env.cr.execute(f"""
            SELECT id
              FROM account_bank_statement st,
                   LATERAL (
                       SELECT balance_end_real
                         FROM account_bank_statement st_lookup
                        WHERE st_lookup.first_line_index < st.first_line_index
                          AND st_lookup.journal_id = st.journal_id
                     ORDER BY st_lookup.first_line_index desc
                        LIMIT 1
                   ) prev
             WHERE prev.balance_end_real != st.balance_start
               {"" if all_statements else "AND st.id IN %(ids)s"}
        """, {
            'ids': tuple(self.ids)
        })
        res = self.env.cr.fetchall()
        return [r[0] for r in res]
