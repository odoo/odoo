# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.tools import html2plaintext
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import get_unaccent_wrapper
from odoo.addons.base.models.res_bank import sanitize_account_number

from xmlrpc.client import MAXINT


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _order = "date desc, name desc, id desc"
    _inherit = ['mail.thread']
    _check_company_auto = True

    @api.model
    def default_get(self, fields_list):
        defaults = super(AccountBankStatement, self).default_get(fields_list)
        # if it is called from the action menu, we can have both start and end balances
        if self._context.get('active_model') == 'account.bank.statement.line' and self._context.get('active_ids'):
            lines = self.env['account.bank.statement.line'].browse(self._context.get('active_ids'))\
                .filtered(lambda line: line.statement_state != 'posted')\
                .sorted('internal_index')
            if not lines:
                raise UserError(_('No editable line selected.'))
            defaults['balance_end_real'] = lines[-1:].running_balance
            defaults['line_ids'] = [Command.set(lines.ids)]

        return defaults

    @api.depends('first_line_id.amount')
    def _compute_balance_start(self):
        for statement in self:
            statement.balance_start = statement.first_line_id.running_balance - statement.first_line_id.amount

    @api.depends('balance_start', 'line_ids.amount')
    def _end_balance(self):
        for statement in self:
            statement.balance_end = statement.balance_start + sum(statement.line_ids.mapped('amount'))

    @api.depends('journal_id')
    def _compute_currency(self):
        for statement in self:
            statement.currency_id = statement.journal_id.currency_id or statement.company_id.currency_id

    @api.depends('line_ids.internal_index')
    def _compute_first_last_lines(self):
        for stmt in self:
            sorted_lines = stmt.line_ids.sorted('internal_index')
            stmt.first_line_id = sorted_lines[:1].id
            stmt.last_line_id = sorted_lines[-1:].id

    def _compute_is_valid(self):
        """
        Check if the statement is valid.
        A statement is valid if:
            - Balance start == First line's `cumulated balance - amount` (it happens when lines before the statement has changed)
            - Balance End == Real balance
        """
        empty_statements = self.filtered(lambda stmt: not stmt.line_ids)
        empty_statements.is_valid = True
        for stmt in (self - empty_statements):
            stmt.is_valid = (
                    not stmt.currency_id.compare_amounts(stmt.balance_end, stmt.balance_end_real)
                    and not stmt.currency_id.compare_amounts(
                            stmt.first_line_id.running_balance - stmt.first_line_id.amount,
                            stmt.balance_start
                    )
            )

    @api.depends('line_ids.journal_id')
    def _compute_journal_id(self):
        for statement in self:
            statement.journal_id = statement.line_ids.journal_id

    @api.depends('balance_end', 'balance_end_real')
    def _compute_state(self):
        for statement in self:
            if statement.state == 'posted':
                # we do not change the state of a posted statement automatically
                continue
            elif statement.currency_id and statement.currency_id.compare_amounts(
                    statement.balance_end,
                    statement.balance_end_real) == 0:
                statement.state = 'complete'
            else:
                statement.state = 'open'

    name = fields.Char(
        string='Reference',
        states={'posted': [('readonly', True)]},
        copy=False,
        index=True,
    )
    reference = fields.Char(
        string='External Reference',
        states={'posted': [('readonly', True)]},
        copy=False,
        help="Used to hold the reference of the external mean that created this statement (name of imported file, reference of online synchronization...)"
    )
    date = fields.Date(related='last_line_id.date', store=True, index=True)

    # Balance start  has to be encoded by the user, but the default value is the last completed or posted
    # statement's real end balance.
    balance_start = fields.Monetary(
        string='Starting Balance',
        compute='_compute_balance_start', store=True, readonly=False,
    )
    balance_end_real = fields.Monetary('Ending Balance', states={'posted': [('readonly', True)]},)
    state = fields.Selection(
        string='Status',
        selection=[
            ('open', 'Open'),
            ('complete', 'Complete'),
            ('posted', 'Posted'),
        ],
        compute='_compute_state',
        store=True,
        help="""The current state of your bank statement:
             - Open: Ending balance does not match.
             - Complete: Ending balance matches the lines, ready for the reconciliation.
             - Posted: validated and locked."""
    )
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', string="Currency")
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True,
        check_company=True,
    )
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True)

    # Balance end is calculated based on the statement line amounts and real starting balance.
    balance_end = fields.Monetary('Computed Balance', compute='_end_balance', store=True,)
    line_ids = fields.One2many(
        comodel_name='account.bank.statement.line',
        inverse_name='statement_id',
        string='Statement lines',
        required=True,
        states={'posted': [('readonly', True)]},
    )

    # first (earliest) and last (latest) statement lines, technical fields for usability purposes
    first_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        compute='_compute_first_last_lines', store=True,
    )
    last_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        compute='_compute_first_last_lines', store=True,
    )

    all_lines_reconciled = fields.Boolean(compute='_compute_all_lines_reconciled') # are all statement lines are fully reconciled?
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    is_valid = fields.Boolean(
        compute="_compute_is_valid"
    )  # used to display a warning message if ending balance is different from the running balance
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
    )

    @api.depends('line_ids.is_reconciled')
    def _compute_all_lines_reconciled(self):
        for statement in self:
            statement.all_lines_reconciled = all(st_line.is_reconciled for st_line in statement.line_ids)

    @api.model
    def _garbage_clean_statements(self):
        """
        Currently it removes the statements with no lines, can be extended if needed.
        """
        self.search([
            ('line_ids', '=', []),
            ('write_date', '<', fields.Date.context_today(self))
        ]).unlink()

    def _post(self):
        # if any(stmt.state != 'complete' for stmt in self):
        #     raise UserError(_("You can only validate statements in the complete state."))
        self.state = 'posted'
        lines_of_moves_to_post = self.line_ids.filtered(lambda line: line.move_id.state != 'posted')
        if lines_of_moves_to_post:
            lines_of_moves_to_post.move_id._post(soft=False)

        self.line_ids.is_anchor = False
        for statement in self:
            statement.line_ids.sorted()[:1].write({
                'is_anchor': True,
                'anchor_value': statement.balance_end_real
            })

            # todo: POMA add statement report
            # Bank statement report.
            # if statement.journal_id.type == 'bank':
            #     content = self.env["ir.actions.report"]._render_qweb_pdf(
            #         'account.action_report_account_statement', statement.id)[:1]
            #     self.attachment_ids += self.env['ir.attachment'].create({
            #         'name': statement.name and _("Bank Statement %s.pdf", statement.name) or _("Bank Statement.pdf"),
            #         'type': 'binary',
            #         'raw': content,
            #     })

    def action_post(self):
        self._post()
        return {'type': 'ir.actions.act_window_close'}

    def _unpost(self):
        self.state = 'open'
        self.line_ids.is_anchor = False
        self.env.add_to_compute(self._fields['state'], self)

    def action_unpost(self):
        self._unpost()
        return {'type': 'ir.actions.act_window_close'}

    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': self.env.ref('account.view_move_line_tree_grouped_bank_cash').id,
            'type': 'ir.actions.act_window',
            'domain': [('move_id', 'in', self.line_ids.move_id.ids)],
            'context': {
                'journal_id': self.journal_id.id,
                'group_by': 'move_id',
                'expand': True
            }
        }

    def name_get(self):
        return [(st.id, f'{st.date or ""} {st.balance_end_real}') if st.line_ids else '/' for st in self]

    def _compute_display_name(self):
        for statement in self:
            statement.display_name = statement.name or ''


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _inherits = {'account.move': 'move_id'}
    _description = "Bank Statement Line"
    _order = "internal_index desc"
    _check_company_auto = True

    # FIXME: Field having the same name in both tables are confusing (partner_id). We don't change it because:
    # - It's a mess to track/fix.
    # - Some fields here could be simplified when the onchanges will be gone in account.move.
    # Should be improved in the future.

    # == Business fields ==
    def default_get(self, fields):
        defaults = super().default_get(fields)
        # override journal_id with the default journal from the move, which is a general journal instead of liquidity
        if 'journal_id' in fields and 'default_journal_id' not in self.env.context:
            defaults['journal_id'] = self._get_default_journal().id
        if 'statement_id' in fields and 'journal_id' in defaults:
            defaults.setdefault(
                'statement_id', self._get_default_statement(defaults.get('journal_id'), defaults.get('date')).id
            )
        return defaults

    move_id = fields.Many2one(
        comodel_name='account.move',
        auto_join=True,
        string='Journal Entry', required=True, readonly=True, ondelete='cascade',
        check_company=True)
    statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
        string='Statement',
    )

    sequence = fields.Integer(help="Gives the sequence order when displaying a list of bank statement lines.", default=1)
    account_number = fields.Char(string='Bank Account Number', help="Technical field used to store the bank account number before its creation, upon the line's processing")
    partner_name = fields.Char(
        help="This field is used to record the third party name when importing bank statement in electronic format, "
             "when the partner doesn't exist yet in the database (or cannot be found).")
    transaction_type = fields.Char(string='Transaction Type')
    payment_ref = fields.Char(string='Label')
    amount = fields.Monetary(currency_field='currency_id')
    amount_currency = fields.Monetary(
        string="Amount in Currency",
        currency_field='foreign_currency_id',
        help="The amount expressed in an optional other currency if it is a multi-currency entry.",
    )
    foreign_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Foreign Currency",
        help="The optional other currency if it is a multi-currency entry.",
    )
    amount_residual = fields.Float(string="Residual Amount",
        compute="_compute_is_reconciled",
        store=True,
        help="The amount left to be reconciled on this statement line (signed according to its move lines' balance), expressed in its currency. This is a technical field use to speedup the application of reconciliation models.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Journal Currency',
        compute='_compute_currency_id', store=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner', ondelete='restrict',
        domain="['|', ('parent_id','=', False), ('is_company','=',True)]",
        check_company=True)
    payment_ids = fields.Many2many(
        comodel_name='account.payment',
        relation='account_payment_account_bank_statement_line_rel',
        string='Auto-generated Payments',
        help="Payments generated during the reconciliation of this bank statement lines.")

    # == Technical fields ==
    internal_index = fields.Char(
        string='Internal Reference',
        compute='_compute_internal_index', store=True,
        index=True,
        help="Technical field used to store the internal reference of the statement line for fast indexing."
    )
    # == Display purpose fields ==
    is_reconciled = fields.Boolean(
        string='Is Reconciled',
        compute='_compute_is_reconciled', store=True,
    )  # Technical field indicating if the statement line is already reconciled.
    statement_state = fields.Selection(
        string='Statement Status',
        related='statement_id.state', readonly=True, store=True
    )
    statement_is_valid = fields.Boolean(
        related='statement_id.is_valid', readonly=True, store=False
    )
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    # Not the values of this field does not necessarily correspond to the cumulated balance in the account move line.
    # here these values correspond to occurrence order (the reality) and the should match the bank report
    # but in the move lines, it corresponds to the recognition order. But these two values should probably be the same
    # at the end of each day.
    running_balance = fields.Monetary(compute='_compute_running_balance')
    # is_anchor is set while validating the statement. It indicates that there is a definite value of the balance
    # based on the real balance of the statement.
    is_anchor = fields.Boolean(readonly=True)
    anchor_value = fields.Monetary(readonly=True)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the liquidity account.
        - The lines using the transfer account.
        - The lines being not in one of the two previous categories.
        :return: (liquidity_lines, suspense_lines, other_lines)
        '''
        liquidity_lines = self.env['account.move.line']
        suspense_lines = self.env['account.move.line']
        other_lines = self.env['account.move.line']

        for line in self.move_id.line_ids:
            if line.account_id == self.journal_id.default_account_id:
                liquidity_lines += line
            elif line.account_id == self.journal_id.suspense_account_id:
                suspense_lines += line
            else:
                other_lines += line
        return liquidity_lines, suspense_lines, other_lines

    def _prepare_counterpart_amounts_using_st_line_rate(self, currency, balance, amount_currency):
        """ Convert the amounts passed as parameters to the statement line currency using the rates provided by the
        bank. The computed amounts are the one that could be set on the statement line as a counterpart journal item
        to fully paid the provided amounts as parameters.

        :param currency:        The currency in which is expressed 'amount_currency'.
        :param balance:         The amount expressed in company currency. Only needed when the currency passed as
                                parameter is neither the statement line's foreign currency, neither the journal's
                                currency.
        :param amount_currency: The amount expressed in the 'currency' passed as parameter.
        :return:                A python dictionary containing:
            * balance:          The amount to consider expressed in company's currency.
            * amount_currency:  The amount to consider expressed in statement line's foreign currency.
        """
        self.ensure_one()
        company_currency, foreign_currency, journal_currency = self._get_currencies()
        company_amount, journal_amount, transaction_amount = self._get_amounts()

        rate_journal2foreign_curr = journal_amount and abs(transaction_amount) / abs(journal_amount)
        rate_comp2journal_curr = company_amount and abs(journal_amount) / abs(company_amount)

        if currency == foreign_currency:
            trans_amount_currency = amount_currency
            if rate_journal2foreign_curr:
                journ_amount_currency = journal_currency.round(trans_amount_currency / rate_journal2foreign_curr)
            else:
                journ_amount_currency = 0.0
            if rate_comp2journal_curr:
                new_balance = company_currency.round(journ_amount_currency / rate_comp2journal_curr)
            else:
                new_balance = 0.0
        elif currency == journal_currency:
            trans_amount_currency = foreign_currency.round(amount_currency * rate_journal2foreign_curr)
            if rate_comp2journal_curr:
                new_balance = company_currency.round(amount_currency / rate_comp2journal_curr)
            else:
                new_balance = 0.0
        else:
            journ_amount_currency = journal_currency.round(balance * rate_comp2journal_curr)
            trans_amount_currency = foreign_currency.round(journ_amount_currency * rate_journal2foreign_curr)
            new_balance = balance

        return {
            'amount_currency': trans_amount_currency,
            'balance': new_balance,
        }

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current account.bank.statement.line
        record.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()

        if not counterpart_account_id:
            counterpart_account_id = self.journal_id.suspense_account_id.id

        if not counterpart_account_id:
            raise UserError(_(
                "You can't create a new statement line without a suspense account set on the %s journal.",
                self.journal_id.display_name,
            ))

        _company_currency, foreign_currency, journal_currency = self._get_currencies()
        company_amount, journal_amount, transaction_amount = self._get_amounts()

        liquidity_line_vals = {
            'name': self.payment_ref,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'account_id': self.journal_id.default_account_id.id,
            'currency_id': journal_currency.id,
            'amount_currency': journal_amount,
            'debit': company_amount > 0 and company_amount or 0.0,
            'credit': company_amount < 0 and -company_amount or 0.0,
        }

        # Create the counterpart line values.
        counterpart_line_vals = {
            'name': self.payment_ref,
            'account_id': counterpart_account_id,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': foreign_currency.id,
            'amount_currency': -transaction_amount,
            'debit': -company_amount if company_amount < 0.0 else 0.0,
            'credit': company_amount if company_amount > 0.0 else 0.0,
        }
        return [liquidity_line_vals, counterpart_line_vals]

    def _get_currencies(self):
        """
        Returns company, journal and foreign currencies of the lines
        """
        self.ensure_one()
        company_currency = self.journal_id.company_id.currency_id
        journal_currency = self.journal_id.currency_id or company_currency
        foreign_currency = self.foreign_currency_id or journal_currency or company_currency
        return company_currency, foreign_currency, journal_currency

    def _get_amounts(self):
        """
        Returns the line amount in company, journal and foreign currencies
        """
        self.ensure_one()
        company_currency, foreign_currency, journal_currency = self._get_currencies()
        journal_amount = self.amount
        if foreign_currency == journal_currency:
            transaction_amount = journal_amount
        else:
            transaction_amount = self.amount_currency
        if journal_currency == company_currency:
            company_amount = journal_amount
        elif foreign_currency == company_currency:
            company_amount = transaction_amount
        else:
            company_amount = journal_currency._convert(journal_amount, company_currency, self.journal_id.company_id, self.date)
        return company_amount, journal_amount, transaction_amount

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    def _compute_running_balance(self):
        line_map = {}

        # Integrating the journal in the queries will make the query more complex, because we have different anchor
        # points per journal, and it should be rare to have a read on multi journal in this model
        self.flush_model(['journal_id', 'is_anchor', 'anchor_value', 'amount', 'internal_index', 'move_id'])
        for journal in self.journal_id:
            journal_lines = self.filtered(lambda line: line.journal_id == journal)
            anchor_line_domain = [
                ('is_anchor', '=', True),
                ('journal_id', '=', journal.id),
            ]

            min_index = min(journal_lines.mapped('internal_index'))
            max_index = max(journal_lines.mapped('internal_index'))
            if min_index:
                anchor_line_domain.append(('internal_index', '<=', min_index))
            # if max_index:
            #     anchor_line_domain.append(('internal_index', '<=', min_index))

            anchor_index = self.search(
                domain=anchor_line_domain,
                order='internal_index desc',
                limit=1
            ).internal_index or ''
            self._cr.execute(
                """
                WITH running_balances AS (
                    SELECT st_line.id as id,
                           anchor_sum(amount, is_anchor, anchor_value)
                               OVER (
                                   ORDER BY internal_index
                                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                               ) as running_balance
                      FROM account_bank_statement_line st_line
                      JOIN account_move ON account_move.id = st_line.move_id
                     WHERE journal_id = %s AND internal_index BETWEEN %s AND %s
                )
                SELECT id,
                       running_balance
                  FROM running_balances
                 WHERE id IN %s
                """,
                [journal.id, anchor_index, max_index, tuple(journal_lines.ids)]
            )
            line_map.update({r[0]: r[1] for r in self.env.cr.fetchall()})
        for record in self:
            record.running_balance = line_map[record.id]

    def _onchange_journal_id(self):
        for line in self:
            line.statement_id = self._get_default_statement(line.journal_id.id, line.date)

    @api.depends('journal_id.currency_id')
    def _compute_currency_id(self):
        for st_line in self:
            st_line.currency_id = st_line.journal_id.currency_id or st_line.company_id.currency_id

    @api.depends('journal_id', 'currency_id', 'amount', 'foreign_currency_id', 'amount_currency',
                 'move_id.to_check',
                 'move_id.line_ids.account_id', 'move_id.line_ids.amount_currency',
                 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.currency_id',
                 'move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    def _compute_is_reconciled(self):
        ''' Compute the field indicating if the statement lines are already reconciled with something.
        This field is used for display purpose (e.g. display the 'cancel' button on the statement lines).
        Also computes the residual amount of the statement line.
        '''
        for st_line in self:
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()

            # Compute residual amount
            if st_line.to_check:
                st_line.amount_residual = -st_line.amount_currency if st_line.foreign_currency_id else -st_line.amount
            elif suspense_lines.account_id.reconcile:
                st_line.amount_residual = sum(suspense_lines.mapped('amount_residual_currency'))
            else:
                st_line.amount_residual = sum(suspense_lines.mapped('amount_currency'))

            # Compute is_reconciled
            if not st_line.id:
                # New record: The journal items are not yet there.
                st_line.is_reconciled = False
            elif suspense_lines:
                # In case of the statement line comes from an older version, it could have a residual amount of zero.
                st_line.is_reconciled = suspense_lines.currency_id.is_zero(st_line.amount_residual)
            elif st_line.currency_id.is_zero(st_line.amount):
                st_line.is_reconciled = True
            else:
                # The journal entry seems reconciled.
                st_line.is_reconciled = True

    @api.depends('date', 'sequence')
    def _compute_internal_index(self):
        """
        Internal index is a field that holds the combination of the date, sequence and id of each line.
        Using this prevents us having a compound index, and extensive where clauses.
        Without this finding lines before current line (which we need for calculating the running balance)
        would need a query like this:
          date < current date OR (date = current date AND sequence > current date) or (
          date = current date AND sequence = current sequence AND id < current id)
        which needs to be repeated all over the code.
        This would be simply "internal index < current internal index" using this field.
        Also, we would need a compound index of date + sequence + id
        on the table which is not possible because date is not in this table (it is in the account move table)
        unless we use a sql view which is more complicated.
        """
        # ensure we are using correct value for reversing sequence in the index (2147483647)
        # NOTE: assert self._fields['sequence'].column_type[1] == 'int4'
        # if for any reason it changes (how unlikely), we need to update this code

        for st_line in self.filtered(lambda line: line._origin.id):
            st_line.internal_index = f'{st_line.date.strftime("%Y%m%d")}' \
                                      f'{MAXINT - st_line.sequence:0>10}' \
                                      f'{st_line._origin.id:0>10}'

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('amount', 'amount_currency', 'currency_id', 'foreign_currency_id', 'journal_id')
    def _check_amounts_currencies(self):
        ''' Ensure the consistency the specified amounts and the currencies. '''

        for st_line in self:
            if st_line.foreign_currency_id == st_line.currency_id:
                raise ValidationError(_("The foreign currency must be different than the journal one: %s", st_line.currency_id.name))
            if not st_line.foreign_currency_id and st_line.amount_currency:
                raise ValidationError(_("You can't provide an amount in foreign currency without specifying a foreign currency."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        counterpart_account_ids = []

        for vals in vals_list:
            if 'statement_id' in vals:
                statement = self.env['account.bank.statement'].browse(vals['statement_id'])
                if statement.state == 'posted':
                    raise ValidationError(_("You can not create a statement line in posted bank statements."))

                if vals.get('journal_id') and statement.journal_id and statement.journal_id.id != vals['journal_id']:
                    # most common case, create st_line by code with default journal is not in the context,
                    # default statement does not take journal into account because it does not have access to
                    # the vals, it is set in the default_get and on_change is not called.
                    del vals['statement_id']

                if 'journal_id' not in vals and statement.journal_id:
                    # Ensure the journal is the same as the statement one.
                    # journal_id is a required field in the view so it should be always available if the user
                    # is creating the record, however, if a sync/import modules tries to add a line to an existing
                    # statement they can omit the journal field because it can be obtained from the statement
                    vals['journal_id'] = statement.journal_id.id

            # Force the move_type to avoid inconsistency with residual 'default_move_type' inside the context.
            vals['move_type'] = 'entry'

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

        # No need for the user to manage their status (from Draft to Posted)
        st_lines.move_id.action_post()
        return st_lines

    def write(self, vals):
        # OVERRIDE
        if 'statement_id' in vals:
            statement = self.env['account.bank.statement'].browse(vals['statement_id'])
            if statement.state == 'posted':
                raise ValidationError(_("You can not add statement lines to a posted bank statements."))
        elif any(st == 'posted' for st in self.statement_id.mapped('state')) and \
                any(field in ['amount', 'date', 'sequence', 'internal_index'] for field in vals.keys()):
            raise ValidationError(_("You can change statement lines in a posted bank statements."))

        if 'date' in vals:
            # prevents error when trying to change the date of a bank statement line and the sequence of the related
            # move does not match the date (the date is in a different period)
            self.move_id.name = '/'

        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_statement_posted(self):
        if any(st == 'posted' for st in self.statement_id.mapped('state')):
            raise ValidationError(_("You can not erase statement lines from posted bank statements."))

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
            journal = st_line.journal_id
            company_currency = journal.company_id.currency_id
            journal_currency = journal.currency_id if journal.currency_id != company_currency else False

            line_vals_list = self._prepare_move_line_default_vals()
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
            if st_line.move_id.journal_id != journal:
                st_line_vals['journal_id'] = journal.id
            if st_line.move_id.partner_id != st_line.partner_id:
                st_line_vals['partner_id'] = st_line.partner_id.id
            st_line.move_id.write(st_line_vals)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _get_st_line_strings_for_matching(self, allowed_fields=None):
        """ Collect the strings that could be used on the statement line to perform some matching.

        :param allowed_fields: A explicit list of fields to consider.
        :return: A list of strings.
        """
        self.ensure_one()

        def _get_text_value(field_name):
            if self._fields[field_name].type == 'html':
                return self[field_name] and html2plaintext(self[field_name])
            else:
                return self[field_name]

        st_line_text_values = []
        if allowed_fields is None or 'payment_ref' in allowed_fields:
            value = _get_text_value('payment_ref')
            if value:
                st_line_text_values.append(value)
        if allowed_fields is None or 'narration' in allowed_fields:
            value = _get_text_value('narration')
            if value:
                st_line_text_values.append(value)
        if allowed_fields is None or 'ref' in allowed_fields:
            value = _get_text_value('ref')
            if value:
                st_line_text_values.append(value)
        return st_line_text_values

    def _get_default_amls_matching_domain(self):
        return [
            # Base domain.
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            # Reconciliation domain.
            ('reconciled', '=', False),
            ('account_id.reconcile', '=', True),
            # Special domain for payments.
            '|',
            ('account_id.account_type', 'not in', ('asset_receivable', 'liability_payable')),
            ('payment_id', '=', False),
            # Special domain for statement lines.
            ('statement_line_id', '!=', self.id),
        ]

    def _retrieve_partner(self):
        self.ensure_one()

        # Retrieve the partner from the statement line.
        if self.partner_id:
            return self.partner_id

        # Retrieve the partner from the bank account.
        if self.account_number:
            account_number_nums = sanitize_account_number(self.account_number)
            if account_number_nums:
                domain = [('sanitized_acc_number', 'ilike', account_number_nums)]
                for extra_domain in ([('company_id', '=', self.company_id.id)], []):
                    bank_accounts = self.env['res.partner.bank'].search(extra_domain + domain)
                    if len(bank_accounts.partner_id) == 1:
                        return bank_accounts.partner_id

        # Retrieve the partner from the partner name.
        if self.partner_name:
            domain = [
                ('parent_id', '=', False),
                ('name', 'ilike', self.partner_name),
            ]
            for extra_domain in ([('company_id', '=', self.company_id.id)], []):
                partner = self.env['res.partner'].search(extra_domain + domain, limit=1)
                if partner:
                    return partner

        # Retrieve the partner from the reconcile models.
        rec_models = self.env['account.reconcile.model'].search([
            ('rule_type', '!=', 'writeoff_button'),
            ('company_id', '=', self.company_id.id),
        ])
        for rec_model in rec_models:
            partner = rec_model._get_partner_from_mapping(self)
            if partner and rec_model._is_applicable_for(self, partner):
                return partner

        # Retrieve the partner from statement line text values.
        st_line_text_values = self._get_st_line_strings_for_matching()
        unaccent = get_unaccent_wrapper(self._cr)
        sub_queries = []
        params = []
        for text_value in st_line_text_values:
            if not text_value:
                continue

            # Find a partner having a name contained inside the statement line values.
            # Take care a partner could contain some special characters in its name that needs to be escaped.
            sub_queries.append(rf'''
                {unaccent("%s")} ~* ('^' || (
                   SELECT STRING_AGG(CONCAT('(?=.*\m', chunk[1], '\M)'), '')
                   FROM regexp_matches({unaccent('name')}, '\w{{3,}}', 'g') AS chunk
                ))
            ''')
            params.append(text_value)

        if sub_queries:
            self.env['res.partner'].flush_model(['company_id', 'name'])
            self._cr.execute(
                '''
                    SELECT id
                    FROM res_partner
                    WHERE (company_id IS NULL OR company_id = %s)
                        AND name IS NOT NULL
                        AND (''' + ') OR ('.join(sub_queries) + ''')
                ''',
                [self.company_id.id] + params,
            )
            rows = self._cr.fetchall()
            if len(rows) == 1:
                return self.env['res.partner'].browse(rows[0][0])

        return self.env['res.partner']

    def _find_or_create_bank_account(self):
        bank_account = self.env['res.partner.bank'].search([
            ('acc_number', '=', self.account_number),
            ('partner_id', '=', self.partner_id.id),
        ])
        if not bank_account:
            bank_account = self.env['res.partner.bank'].create({
                'acc_number': self.account_number,
                'partner_id': self.partner_id.id,
            })
        return bank_account

    @api.model
    def _get_default_journal(self):
        journal_type = self.env.context.get('journal_type', 'bank')
        return self.env['account.journal'].search([
                ('type', '=', journal_type),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

    @api.model
    def _get_default_statement(self, journal_id=None, date=None):
        return self.search(
            domain=[
                ('journal_id', '=', journal_id or self._get_default_journal().id),
                ('statement_id', '!=', False),
                ('statement_state', '=', 'open'),
                ('date', '<=', date or fields.Date.today()),
            ],
            limit=1
        ).statement_id

    def button_undo_reconciliation(self):
        ''' Undo the reconciliation mades on the statement line and reset their journal items
        to their original states.
        '''
        self.line_ids.remove_move_reconcile()
        self.payment_ids.unlink()

        for st_line in self:
            st_line.with_context(force_delete=True).write({
                'to_check': False,
                'line_ids': [Command.clear()] + [Command.create(line_vals) for line_vals in st_line._prepare_move_line_default_vals()],
            })
    def action_post(self):
        self.move_id.filtered(lambda move: move.state == 'draft').action_post()

# For optimization purpose, creating the reverse relation of m2o in _inherits saves
# a lot of SQL queries
class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['account.move']

    statement_line_ids = fields.One2many('account.bank.statement.line', 'move_id', string='Statements')
