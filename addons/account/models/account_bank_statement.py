# -*- coding: utf-8 -*-
from contextlib import contextmanager

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class AccountBankStatement(models.Model):
    _name = 'account.bank.statement'
    _description = "Bank Statement"
    _order = "first_line_index desc"
    _check_company_auto = True

    name = fields.Char(
        string='Reference',
        compute='_compute_name', store=True, readonly=False,
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
        index=True,
    )

    # The internal index of the first line of a statement, it is used for sorting the statements
    # The date field cannot be used as there might be more than one statement in one day.
    # keeping this order is important because the validity of the statements are based on their order
    first_line_index = fields.Char(
        comodel_name='account.bank.statement.line',
        compute='_compute_date_index', store=True,
    )

    balance_start = fields.Monetary(
        string='Starting Balance',
        compute='_compute_balance_start', store=True, readonly=False,
    )

    # Balance end is calculated based on the statement line amounts and real starting balance.
    balance_end = fields.Monetary(
        string='Computed Balance',
        compute='_compute_balance_end', store=True,
    )

    balance_end_real = fields.Monetary(
        string='Ending Balance',
        compute='_compute_balance_end_real', store=True, readonly=False,
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
    )

    # A statement assumed to be complete when the sum of encoded lines is equal to the difference between start and
    # end balances.
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

    problem_description = fields.Text(
        compute='_compute_problem_description',
    )

    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Attachments",
    )

    _journal_id_date_desc_id_desc_idx = models.Index("(journal_id, date DESC, id DESC)")
    _first_line_index_idx = models.Index("(journal_id, first_line_index)")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('create_date')
    def _compute_name(self):
        for stmt in self:
            name = ''
            if stmt.journal_id:
                name = stmt.journal_id.code + ' '
            stmt.name = name +_("Statement %(date)s", date=stmt.date or fields.Date.to_date(stmt.create_date))

    @api.depends('line_ids.internal_index', 'line_ids.state')
    def _compute_date_index(self):
        for stmt in self:
            # When we create lines manually from the form view, they don't have any `internal_index` set yet.
            sorted_lines = stmt.line_ids.filtered("internal_index").sorted('internal_index')
            stmt.first_line_index = sorted_lines[:1].internal_index
            stmt.date = sorted_lines.filtered(lambda l: l.state == 'posted')[-1:].date

    @api.depends('create_date')
    def _compute_balance_start(self):
        for stmt in self.sorted(lambda x: x.first_line_index or '0'):
            journal_id = stmt.journal_id.id or stmt.line_ids.journal_id.id
            previous_line_with_statement = self.env['account.bank.statement.line'].search([
                ('internal_index', '<', stmt.first_line_index),
                ('journal_id', '=', journal_id),
                ('state', '=', 'posted'),
                ('statement_id', '!=', False),
            ], limit=1)
            balance_start = previous_line_with_statement.statement_id.balance_end_real

            lines_in_between_domain = [
                ('internal_index', '<', stmt.first_line_index),
                ('journal_id', '=', journal_id),
                ('state', '=', 'posted'),
            ]
            if previous_line_with_statement:
                lines_in_between_domain.append(('internal_index', '>', previous_line_with_statement.internal_index))
                # remove lines from previous statement (when multi-editing a line already in another statement)
                previous_st_lines = previous_line_with_statement.statement_id.line_ids
                lines_in_common = previous_st_lines.filtered(lambda l: l.id in stmt.line_ids._origin.ids)
                balance_start -= sum(lines_in_common.mapped('amount'))

            lines_in_between = self.env['account.bank.statement.line'].search(lines_in_between_domain)
            balance_start += sum(lines_in_between.mapped('amount'))

            stmt.balance_start = balance_start

    @api.depends('balance_start', 'line_ids.amount', 'line_ids.state')
    def _compute_balance_end(self):
        for stmt in self:
            lines = stmt.line_ids.filtered(lambda x: x.state == 'posted')
            stmt.balance_end = stmt.balance_start + sum(lines.mapped('amount'))

    @api.depends('balance_start')
    def _compute_balance_end_real(self):
        for stmt in self:
            stmt.balance_end_real = stmt.balance_end

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for statement in self:
            statement.currency_id = statement.journal_id.currency_id or statement.company_id.currency_id

    @api.depends('line_ids.journal_id')
    def _compute_journal_id(self):
        for statement in self:
            statement.journal_id = statement.line_ids.journal_id

    @api.depends('balance_end', 'balance_end_real', 'line_ids.amount', 'line_ids.state')
    def _compute_is_complete(self):
        for stmt in self:
            stmt.is_complete = stmt.line_ids.filtered(lambda l: l.state == 'posted') and stmt.currency_id.compare_amounts(
                stmt.balance_end, stmt.balance_end_real) == 0

    @api.depends('balance_end', 'balance_end_real')
    def _compute_is_valid(self):
        # we extract the invalid statements, the statements with no lines and the first statement are not in the query
        # because they don't have a previous statement, so they are excluded from the join, and we consider them valid.
        # if we have extracted the valid ones, we would have to mark above-mentioned statements valid manually
        # For new statements, a sql query can't be used
        if len(self) == 1:
            self.is_valid = self._get_statement_validity()
        else:
            invalids = self.filtered(lambda s: s.id in self._get_invalid_statement_ids())
            invalids.is_valid = False
            (self - invalids).is_valid = True

    @api.depends('is_valid', 'is_complete')
    def _compute_problem_description(self):
        for stmt in self:
            description = None
            if not stmt.is_valid:
                description = _("The starting balance doesn't match the ending balance of the previous statement, or an earlier statement is missing.")
            elif not stmt.is_complete:
                description = _("The running balance (%s) doesn't match the specified ending balance.", formatLang(self.env, stmt.balance_end, currency_obj=stmt.currency_id))
            stmt.problem_description = description

    def _search_is_valid(self, operator, value):
        if operator not in ('=', '!=', '<>'):
            raise UserError(_('Operation not supported'))
        invalid_ids = self._get_invalid_statement_ids(all_statements=True)
        if operator in ('!=', '<>') and value or operator == '=' and not value:
            return [('id', 'in', invalid_ids)]
        return [('id', 'not in', invalid_ids)]

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def _get_statement_validity(self):
        """ Compares the balance_start to the previous statements balance_end_real """
        self.ensure_one()
        previous = self.env['account.bank.statement'].search(
            [
                ('first_line_index', '<', self.first_line_index),
                ('journal_id', '=', self.journal_id.id),
            ],
            limit=1,
            order='first_line_index DESC',
        )
        return not previous or self.currency_id.compare_amounts(self.balance_start, previous.balance_end_real) == 0

    def _get_invalid_statement_ids(self, all_statements=None):
        """ Returns the statements that are invalid for _compute and _search methods."""

        self.env['account.bank.statement.line'].flush_model(['statement_id', 'internal_index'])
        self.env['account.bank.statement'].flush_model(['balance_start', 'balance_end_real', 'first_line_index'])

        self.env.cr.execute(f"""
            SELECT st.id
              FROM account_bank_statement st
         LEFT JOIN res_company co ON st.company_id = co.id
         LEFT JOIN account_journal j ON st.journal_id = j.id
         LEFT JOIN res_currency currency ON COALESCE(j.currency_id, co.currency_id) = currency.id,
                   LATERAL (
                       SELECT balance_end_real
                         FROM account_bank_statement st_lookup
                        WHERE st_lookup.first_line_index < st.first_line_index
                          AND st_lookup.journal_id = st.journal_id
                     ORDER BY st_lookup.first_line_index desc
                        LIMIT 1
                   ) prev
             WHERE ROUND(prev.balance_end_real, currency.decimal_places) != ROUND(st.balance_start, currency.decimal_places)
               {"" if all_statements else "AND st.id IN %(ids)s"}
        """, {
            'ids': tuple(self.ids)
        })
        res = self.env.cr.fetchall()
        return [r[0] for r in res]

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        # EXTENDS base
        defaults = super().default_get(fields_list)

        if 'line_ids' not in fields_list:
            return defaults

        active_ids = self._context.get('active_ids', [])
        context_split_line_id = self._context.get('split_line_id')
        context_st_line_id = self._context.get('st_line_id')
        lines = None
        # creating statements with split button
        if context_split_line_id:
            current_st_line = self.env['account.bank.statement.line'].browse(context_split_line_id)
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
        # single line edit
        elif context_st_line_id and len(active_ids) <= 1:
            lines = self.env['account.bank.statement.line'].browse(context_st_line_id)
        # multi edit
        elif context_st_line_id and len(active_ids) > 1:
            lines = self.env['account.bank.statement.line'].browse(active_ids).sorted()
            if len(lines.journal_id) > 1:
                raise UserError(_("A statement should only contain lines from the same journal."))
            # Check that the selected lines are contiguous
            indexes = lines.mapped('internal_index')
            count_lines_between = self.env['account.bank.statement.line'].search_count([
                ('internal_index', '>=', min(indexes)),
                ('internal_index', '<=', max(indexes)),
                ('journal_id', '=', lines.journal_id.id),
            ])
            if len(lines) != count_lines_between:
                raise UserError(_("Unable to create a statement due to missing transactions. You may want to reorder the transactions before proceeding."))

        if lines:
            defaults['line_ids'] = [Command.set(lines.ids)]

        return defaults

    @contextmanager
    def _check_attachments(self, container, values_list):
        attachments_to_fix_list = []
        for values in values_list:
            attachment_ids = set()
            for orm_command in values.get('attachment_ids', []):
                if orm_command[0] == Command.LINK:
                    attachment_ids.add(orm_command[1])
                elif orm_command[0] == Command.SET:
                    for attachment_id in orm_command[2]:
                        attachment_ids.add(attachment_id)

            attachments = self.env['ir.attachment'].browse(list(attachment_ids))
            attachments_to_fix_list.append(attachments)

        yield

        for stmt, attachments in zip(container['records'], attachments_to_fix_list):
            attachments.write({'res_id': stmt.id, 'res_model': stmt._name})

    @api.model_create_multi
    def create(self, vals_list):
        container = {'records': self.env['account.bank.statement']}
        with self._check_attachments(container, vals_list):
            container['records'] = stmts = super().create(vals_list)
        return stmts

    def write(self, values):
        if len(self) != 1 and 'attachment_ids' in values:
            values.pop('attachment_ids')

        container = {'records': self}
        with self._check_attachments(container, [values]):
            result = super().write(values)
        return result
